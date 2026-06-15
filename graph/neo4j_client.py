"""
Neo4j Database Client for LegalKG

Handles connection, schema management, and Cypher query execution.
"""

import os
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from datetime import datetime

from neo4j import GraphDatabase, Session, Driver
from neo4j.exceptions import ServiceUnavailable, AuthError, DatabaseError

from ingestion.utils import get_logger


logger = get_logger("legalkg.neo4j_client")


@dataclass
class Neo4jConfig:
    """Neo4j connection configuration."""
    uri: str = "neo4j://localhost:7687"
    username: str = "neo4j"
    password: str = "password"
    database: str = "neo4j"
    max_retries: int = 3


class Neo4jClient:
    """Neo4j database client with connection management."""
    
    def __init__(
        self,
        uri: str = None,
        username: str = None,
        password: str = None,
        database: str = None,
    ):
        """
        Initialize Neo4j client.
        
        Args:
            uri: Connection URI (default from env or config)
            username: Username (default from env)
            password: Password (default from env)
            database: Database name (default from env or 'neo4j')
        """
        self.config = Neo4jConfig(
            uri=uri or os.getenv("NEO4J_URI", "neo4j://localhost:7687"),
            username=username or os.getenv("NEO4J_USERNAME", "neo4j"),
            password=password or os.getenv("NEO4J_PASSWORD", "password"),
            database=database or os.getenv("NEO4J_DATABASE", "neo4j"),
        )
        
        self._driver: Optional[Driver] = None
        self._connected = False
        
    def connect(self) -> bool:
        """
        Connect to Neo4j database.
        
        Returns:
            True if connection successful, False otherwise
        """
        try:
            self._driver = GraphDatabase.driver(
                self.config.uri,
                auth=(self.config.username, self.config.password),
            )
            self._driver.verify_connectivity()
            self._connected = True
            logger.info(f"✅ Connected to Neo4j: {self.config.uri}")
            return True
        except AuthError as e:
            logger.error(f"❌ Authentication failed: {e}")
            return False
        except ServiceUnavailable as e:
            logger.error(f"❌ Neo4j service unavailable: {e}")
            return False
        except Exception as e:
            logger.error(f"❌ Connection failed: {e}")
            return False
    
    def disconnect(self) -> None:
        """Disconnect from Neo4j database."""
        if self._driver:
            self._driver.close()
            self._connected = False
            logger.info("Disconnected from Neo4j")
    
    def is_connected(self) -> bool:
        """Check if connected to database."""
        return self._connected
    
    def execute_query(
        self,
        query: str,
        parameters: Dict[str, Any] = None,
        database: str = None,
    ) -> List[Dict[str, Any]]:
        """
        Execute a single Cypher query.
        
        Args:
            query: Cypher query
            parameters: Query parameters
            database: Database name (overrides default)
            
        Returns:
            List of result records
        """
        if not self._connected:
            logger.error("Not connected to database")
            return []
        
        try:
            with self._driver.session(database=database or self.config.database) as session:
                result = session.run(query, parameters or {})
                records = [record.data() for record in result]
                logger.debug(f"Query executed, {len(records)} records returned")
                return records
        except Exception as e:
            logger.error(f"Query execution failed: {e}\nQuery: {query}")
            return []
    
    def execute_write_transaction(
        self,
        query: str,
        parameters: Dict[str, Any] = None,
        database: str = None,
    ) -> Dict[str, Any]:
        """
        Execute a write transaction.
        
        Args:
            query: Cypher query
            parameters: Query parameters
            database: Database name
            
        Returns:
            Transaction result with summary info
        """
        if not self._connected:
            logger.error("Not connected to database")
            return {"success": False, "error": "Not connected"}
        
        try:
            with self._driver.session(database=database or self.config.database) as session:
                result = session.write_transaction(
                    self._execute_write,
                    query,
                    parameters or {},
                )
                return result
        except Exception as e:
            logger.error(f"Write transaction failed: {e}")
            return {"success": False, "error": str(e)}
    
    @staticmethod
    def _execute_write(tx, query: str, parameters: Dict) -> Dict:
        """Execute write within transaction."""
        result = tx.run(query, parameters)
        summary = result.consume()
        return {
            "success": True,
            "nodes_created": summary.counters.nodes_created,
            "relationships_created": summary.counters.relationships_created,
            "properties_set": summary.counters.properties_set,
            "indexes_added": summary.counters.indexes_added,
            "constraints_added": summary.counters.constraints_added,
        }
    
    def batch_create_nodes(
        self,
        label: str,
        nodes: List[Dict[str, Any]],
        batch_size: int = 1000,
    ) -> Dict[str, Any]:
        """
        Batch create nodes of same label.
        
        Args:
            label: Node label
            nodes: List of node properties
            batch_size: Batch size for processing
            
        Returns:
            Result statistics
        """
        total_created = 0
        failed_batches = 0
        
        for i in range(0, len(nodes), batch_size):
            batch = nodes[i : i + batch_size]
            
            # Create UNWIND query for batch
            query = f"""
            UNWIND $nodes AS node
            MERGE (n:{label} {{id: node.id}})
            SET n += node
            """
            
            result = self.execute_write_transaction(
                query,
                {"nodes": batch},
            )
            
            if result.get("success"):
                total_created += result.get("nodes_created", 0)
            else:
                failed_batches += 1
                logger.warning(f"Failed batch {i//batch_size}: {result.get('error')}")
        
        logger.info(f"Batch create {label}: {total_created} nodes, {failed_batches} failed")
        return {
            "label": label,
            "total_created": total_created,
            "failed_batches": failed_batches,
        }
    
    def batch_create_relationships(
        self,
        rel_data: List[Dict[str, Any]],
        batch_size: int = 1000,
    ) -> Dict[str, Any]:
        """
        Batch create relationships.
        
        Args:
            rel_data: List of relationship data (source_id, target_id, type, properties)
            batch_size: Batch size
            
        Returns:
            Result statistics
        """
        total_created = 0
        failed_batches = 0
        
        for i in range(0, len(rel_data), batch_size):
            batch = rel_data[i : i + batch_size]
            
            query = """
            UNWIND $relationships AS rel
            MATCH (source {id: rel.source_id}), (target {id: rel.target_id})
            CALL apoc.create.relationship(source, rel.type, rel.properties, target)
            YIELD rel AS relationship
            RETURN COUNT(relationship) as count
            """
            
            result = self.execute_write_transaction(
                query,
                {"relationships": batch},
            )
            
            if result.get("success"):
                total_created += result.get("relationships_created", 0)
            else:
                failed_batches += 1
        
        logger.info(f"Batch create relationships: {total_created} rels, {failed_batches} failed")
        return {
            "total_created": total_created,
            "failed_batches": failed_batches,
        }
    
    def get_schema_info(self) -> Dict[str, Any]:
        """Get schema information (labels, relationships, indexes)."""
        try:
            # Get labels
            labels_result = self.execute_query(
                "CALL db.labels() YIELD label RETURN label"
            )
            labels = [r["label"] for r in labels_result]
            
            # Get relationships
            rels_result = self.execute_query(
                "CALL db.relationshipTypes() YIELD relationshipType RETURN relationshipType"
            )
            relationship_types = [r["relationshipType"] for r in rels_result]
            
            # Get indexes
            indexes_result = self.execute_query(
                "SHOW INDEXES YIELD name, entityType, state"
            )
            
            # Get constraints
            constraints_result = self.execute_query(
                "SHOW CONSTRAINTS YIELD name, type"
            )
            
            return {
                "labels": labels,
                "relationship_types": relationship_types,
                "indexes": indexes_result,
                "constraints": constraints_result,
            }
        except Exception as e:
            logger.error(f"Failed to get schema info: {e}")
            return {}
    
    def clear_database(self, confirm: bool = False) -> bool:
        """
        Clear all data from database (CAUTION!).
        
        Args:
            confirm: Must be True to execute
            
        Returns:
            True if successful
        """
        if not confirm:
            logger.warning("Database clear cancelled (confirmation required)")
            return False
        
        try:
            result = self.execute_write_transaction("MATCH (n) DETACH DELETE n")
            logger.warning(f"Database cleared: {result}")
            return result.get("success", False)
        except Exception as e:
            logger.error(f"Failed to clear database: {e}")
            return False
    
    def health_check(self) -> Dict[str, Any]:
        """Check Neo4j health status."""
        try:
            result = self.execute_query(
                "RETURN datetime() as timestamp, 'pong' as status"
            )
            if result:
                return {"status": "healthy", "timestamp": result[0].get("timestamp")}
            return {"status": "unhealthy", "error": "No response"}
        except Exception as e:
            return {"status": "unhealthy", "error": str(e)}


def create_neo4j_client() -> Neo4jClient:
    """Create and connect Neo4j client."""
    client = Neo4jClient()
    if not client.connect():
        logger.error("Failed to create Neo4j client")
        return None
    return client
