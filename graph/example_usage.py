"""
TAHAP 3 Example Usage - Graph Loading & Configuration

Demonstrates how to:
1. Connect to Neo4j
2. Create schema & constraints
3. Load enriched content
4. Setup vector indexes
5. Perform semantic search
"""

import os
import json
from pathlib import Path

from graph.neo4j_client import Neo4jClient, create_neo4j_client
from graph.graph_loader import GraphLoader, LoaderConfig
from graph.vector_manager import VectorManager, VectorConfig, setup_vector_indexes
from ingestion.utils import get_logger


logger = get_logger("legalkg.tahap3_example", log_level="INFO")


def example_setup_neo4j_schema():
    """Example 1: Setup Neo4j schema with constraints and indexes."""
    logger.info("\n" + "="*80)
    logger.info("EXAMPLE 1: Setup Neo4j Schema")
    logger.info("="*80)
    
    # Connect to Neo4j
    client = Neo4jClient(
        uri=os.getenv("NEO4J_URI", "neo4j://localhost:7687"),
        username=os.getenv("NEO4J_USERNAME", "neo4j"),
        password=os.getenv("NEO4J_PASSWORD", "password"),
    )
    
    if not client.connect():
        logger.error("Failed to connect to Neo4j")
        return
    
    # Read and execute schema script
    schema_file = Path("graph/schemas/legal_schema.cypher")
    if not schema_file.exists():
        logger.error(f"Schema file not found: {schema_file}")
        client.disconnect()
        return
    
    with open(schema_file) as f:
        schema_lines = f.readlines()
    
    # Extract Cypher statements (skip comments and empty lines)
    statements = []
    current_statement = []
    
    for line in schema_lines:
        line = line.rstrip()
        
        # Skip comments
        if line.startswith("//"):
            continue
        
        # Skip empty lines
        if not line.strip():
            if current_statement:
                statements.append(" ".join(current_statement))
                current_statement = []
            continue
        
        current_statement.append(line)
    
    if current_statement:
        statements.append(" ".join(current_statement))
    
    # Execute each statement
    logger.info(f"Executing {len(statements)} schema statements...")
    
    for idx, statement in enumerate(statements):
        if not statement.strip():
            continue
        
        logger.debug(f"Statement {idx+1}: {statement[:100]}...")
        
        try:
            result = client.execute_write_transaction(statement)
            if result.get("success"):
                logger.info(f"✅ Statement {idx+1} executed")
                if result.get("constraints_added"):
                    logger.info(f"   Constraints added: {result['constraints_added']}")
                if result.get("indexes_added"):
                    logger.info(f"   Indexes added: {result['indexes_added']}")
        except Exception as e:
            logger.warning(f"Statement {idx+1} failed: {e}")
    
    # Verify schema
    logger.info("\n📋 Verifying schema...")
    schema_info = client.get_schema_info()
    logger.info(f"  Labels: {', '.join(schema_info.get('labels', []))}")
    logger.info(f"  Relationships: {', '.join(schema_info.get('relationship_types', []))}")
    logger.info(f"  Indexes: {len(schema_info.get('indexes', []))}")
    logger.info(f"  Constraints: {len(schema_info.get('constraints', []))}")
    
    client.disconnect()


def example_load_enriched_content():
    """Example 2: Load enriched content from TAHAP 2."""
    logger.info("\n" + "="*80)
    logger.info("EXAMPLE 2: Load Enriched Content into Graph")
    logger.info("="*80)
    
    # Connect to Neo4j
    client = create_neo4j_client()
    if not client:
        logger.error("Failed to connect to Neo4j")
        return
    
    # Create loader
    loader_config = LoaderConfig(batch_size=500)
    loader = GraphLoader(client, loader_config)
    
    # Load from JSON file
    enriched_file = Path("data/enriched_content.json")
    if not enriched_file.exists():
        logger.error(f"Enriched content file not found: {enriched_file}")
        logger.info("Run TAHAP 1 + TAHAP 2 first to generate data")
        client.disconnect()
        return
    
    logger.info(f"Loading from {enriched_file}...")
    
    try:
        with open(enriched_file) as f:
            data = json.load(f)
        
        logger.info(f"Loaded {len(data)} documents")
        
        # Load documents
        stats = loader.load_enriched_documents(data)
        
        logger.info("\n✅ Loading complete!")
        logger.info(f"  Peraturan created: {stats['peraturan_created']}")
        logger.info(f"  Pasal created: {stats['pasal_created']}")
        logger.info(f"  Ayat created: {stats['ayat_created']}")
        logger.info(f"  KonsepHukum created: {stats['konsep_created']}")
        logger.info(f"  Relationships created: {stats['relationships_created']}")
        
    except Exception as e:
        logger.error(f"Failed to load content: {e}")
    
    client.disconnect()


def example_setup_vector_indexes():
    """Example 3: Setup vector indexes."""
    logger.info("\n" + "="*80)
    logger.info("EXAMPLE 3: Setup Vector Indexes")
    logger.info("="*80)
    
    # Connect to Neo4j
    client = create_neo4j_client()
    if not client:
        logger.error("Failed to connect to Neo4j")
        return
    
    # Create vector indexes
    logger.info("Creating vector indexes...")
    
    try:
        success = setup_vector_indexes(client)
        
        if success:
            logger.info("✅ Vector indexes created")
            
            # Check indexes
            indexes = client.execute_query(
                "SHOW INDEXES WHERE name LIKE '%embedding%'"
            )
            
            logger.info(f"  Total embedding indexes: {len(indexes)}")
            for idx in indexes:
                logger.info(f"    - {idx.get('name')}: {idx.get('state')}")
        else:
            logger.error("Failed to create vector indexes")
    
    except Exception as e:
        logger.error(f"Error: {e}")
    
    client.disconnect()


def example_semantic_search():
    """Example 4: Semantic search (requires embeddings)."""
    logger.info("\n" + "="*80)
    logger.info("EXAMPLE 4: Semantic Search")
    logger.info("="*80)
    
    # Connect to Neo4j
    client = create_neo4j_client()
    if not client:
        logger.error("Failed to connect to Neo4j")
        return
    
    # Create vector manager
    vector_config = VectorConfig(provider="openai")
    vector_manager = VectorManager(
        client,
        vector_config,
        api_key=os.getenv("OPENAI_API_KEY"),
    )
    
    # Test semantic search
    query = "Transaksi Elektronik dan Informasi Elektronik"
    
    logger.info(f"🔍 Searching for: {query}")
    
    try:
        # Search pasals
        logger.info("\n📄 Searching Pasals...")
        pasal_results = vector_manager.semantic_search_pasal(query, top_k=3)
        
        if pasal_results:
            for idx, result in enumerate(pasal_results):
                logger.info(f"  [{idx+1}] Pasal {result.get('nomor')} (score: {result.get('score'):.4f})")
                logger.info(f"      {result.get('judul')}")
        else:
            logger.info("  No results found (may need to generate embeddings first)")
        
        # Search concepts
        logger.info("\n💡 Searching Concepts...")
        konsep_results = vector_manager.semantic_search_konsep(query, top_k=3)
        
        if konsep_results:
            for idx, result in enumerate(konsep_results):
                logger.info(f"  [{idx+1}] {result.get('nama')} (score: {result.get('score'):.4f})")
                logger.info(f"      Freq: {result.get('frequency')}")
        else:
            logger.info("  No results found (may need to generate embeddings first)")
    
    except Exception as e:
        logger.error(f"Search failed: {e}")
    
    client.disconnect()


def example_graph_statistics():
    """Example 5: Get graph statistics."""
    logger.info("\n" + "="*80)
    logger.info("EXAMPLE 5: Graph Statistics")
    logger.info("="*80)
    
    # Connect to Neo4j
    client = create_neo4j_client()
    if not client:
        logger.error("Failed to connect to Neo4j")
        return
    
    try:
        # Count nodes by label
        logger.info("📊 Node counts:")
        
        for label in ["Peraturan", "Pasal", "Ayat", "KonsepHukum"]:
            query = f"MATCH (n:{label}) RETURN COUNT(n) as count"
            result = client.execute_query(query)
            
            if result:
                count = result[0].get("count", 0)
                logger.info(f"  {label}: {count}")
        
        # Count relationships by type
        logger.info("\n📋 Relationship counts:")
        
        for rel_type in ["BAGIAN_DARI", "MERUJUK_KE", "MENGATUR"]:
            query = f"MATCH ()-[r:{rel_type}]->() RETURN COUNT(r) as count"
            result = client.execute_query(query)
            
            if result:
                count = result[0].get("count", 0)
                logger.info(f"  {rel_type}: {count}")
        
        # Get schema info
        logger.info("\n🔧 Schema Info:")
        schema_info = client.get_schema_info()
        logger.info(f"  Indexes: {len(schema_info.get('indexes', []))}")
        logger.info(f"  Constraints: {len(schema_info.get('constraints', []))}")
    
    except Exception as e:
        logger.error(f"Failed to get statistics: {e}")
    
    client.disconnect()


def main():
    """Run all examples."""
    logger.info("\n" + "█"*80)
    logger.info("█" + " "*78 + "█")
    logger.info("█" + " "*20 + "TAHAP 3: GRAPH CONFIGURATION & LOADING" + " "*21 + "█")
    logger.info("█" + " "*78 + "█")
    logger.info("█"*80 + "\n")
    
    logger.info("📌 Prerequisites:")
    logger.info("  1. NEO4J_URI = neo4j://localhost:7687 (or set in env)")
    logger.info("  2. NEO4J_USERNAME = neo4j")
    logger.info("  3. NEO4J_PASSWORD = password")
    logger.info("  4. TAHAP 1 + TAHAP 2 output (enriched_content.json)")
    
    # Run examples
    example_setup_neo4j_schema()
    example_load_enriched_content()
    example_setup_vector_indexes()
    example_graph_statistics()
    example_semantic_search()
    
    logger.info("\n" + "█"*80)
    logger.info("✅ TAHAP 3 Examples Complete!")
    logger.info("█"*80 + "\n")


if __name__ == "__main__":
    main()
