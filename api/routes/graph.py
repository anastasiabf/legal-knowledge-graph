"""
Graph Routes - Graph Exploration
"""

from fastapi import APIRouter, HTTPException, Depends
import logging

from api.models import GraphExploreRequest, GraphExploreResponse, GraphNode, GraphEdge, ErrorResponse
from api.main import app_state


logger = logging.getLogger("legalkg.api.graph")
router = APIRouter()


def get_neo4j():
    """Get Neo4j client."""
    if not app_state["neo4j_client"]:
        raise HTTPException(
            status_code=503,
            detail="Neo4j connection not available"
        )
    return app_state["neo4j_client"]


@router.post("/explore", response_model=GraphExploreResponse, responses={503: {"model": ErrorResponse}})
async def explore_graph(request: GraphExploreRequest, neo4j_client = Depends(get_neo4j)):
    """
    Explore graph around a concept.
    
    - **concept**: Legal concept to explore
    - **depth**: Traversal depth (1-5)
    - **limit**: Maximum nodes to return (1-100)
    """
    try:
        logger.info(f"Graph exploration: {request.concept}")
        
        # Find concept node
        concept_query = """
        MATCH (k:KonsepHukum)
        WHERE tolower(k.nama) CONTAINS tolower($concept)
        RETURN k.nama as nama, k.id as id
        LIMIT 1
        """
        
        concept_result = neo4j_client.execute_query(concept_query, concept=request.concept)
        
        if not concept_result:
            raise HTTPException(
                status_code=404,
                detail=f"Concept '{request.concept}' not found"
            )
        
        center_concept = concept_result[0].get("nama")
        
        # Get related nodes
        nodes_query = f"""
        MATCH (k:KonsepHukum {{nama: $concept}})
        CALL apoc.path.subgraphAll(k, {{relationshipFilter: "MENGATUR|TERKAIT_DENGAN", maxLevel: $depth}})
        YIELD nodes, relationships
        UNWIND nodes AS node
        RETURN DISTINCT 
            node.id as id, 
            labels(node)[0] as type,
            CASE 
                WHEN node:KonsepHukum THEN node.nama
                WHEN node:Pasal THEN node.nomor
                WHEN node:Peraturan THEN node.nomor
                ELSE node.id
            END as label,
            properties(node) as props
        LIMIT $limit
        """
        
        try:
            # Fallback if APOC not available
            nodes_query = """
            MATCH (k:KonsepHukum {nama: $concept})
            MATCH (p:Pasal)-[:MENGATUR]->(k)
            RETURN 
                k.id as id, 'KonsepHukum' as type, k.nama as label,
                properties(k) as props
            UNION
            MATCH (k:KonsepHukum {nama: $concept})
            MATCH (k)-[:MENGATUR]->(p:Pasal)
            RETURN 
                p.id as id, 'Pasal' as type, p.nomor as label,
                properties(p) as props
            LIMIT $limit
            """
            
            nodes_result = neo4j_client.execute_query(
                nodes_query,
                concept=center_concept,
                limit=request.limit,
            )
        except:
            nodes_result = []
        
        # Convert to response format
        nodes = [
            GraphNode(
                id=n.get("id", ""),
                label=n.get("label", ""),
                type=n.get("type", "Unknown"),
                properties=n.get("props", {}),
            )
            for n in nodes_result
        ]
        
        # Get relationships
        edges_query = """
        MATCH (n1)-[r]->(n2)
        WHERE n1.nama = $concept OR n2.nama = $concept
        RETURN 
            n1.id as source,
            n2.id as target,
            type(r) as rel_type,
            properties(r) as props
        LIMIT $limit
        """
        
        try:
            edges_result = neo4j_client.execute_query(
                edges_query,
                concept=center_concept,
                limit=request.limit,
            )
        except:
            edges_result = []
        
        # Convert to response format
        edges = [
            GraphEdge(
                source=e.get("source", ""),
                target=e.get("target", ""),
                type=e.get("rel_type", ""),
                properties=e.get("props", {}),
            )
            for e in edges_result
        ]
        
        return GraphExploreResponse(
            nodes=nodes,
            edges=edges,
            center_node=center_concept,
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Graph exploration failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Graph exploration failed: {str(e)}"
        )


@router.get("/concepts", tags=["graph"])
async def list_concepts(
    skip: int = 0,
    limit: int = 20,
    neo4j_client = Depends(get_neo4j)
):
    """
    List all legal concepts.
    
    - **skip**: Number to skip
    - **limit**: Max results (1-100)
    """
    try:
        limit = min(limit, 100)
        
        query = """
        MATCH (k:KonsepHukum)
        RETURN k.nama as nama, k.definisi as definisi,
               k.frequency as frequency, k.confidence as confidence
        ORDER BY k.frequency DESC
        SKIP $skip
        LIMIT $limit
        """
        
        results = neo4j_client.execute_query(query, skip=skip, limit=limit)
        
        # Get total
        count_query = "MATCH (k:KonsepHukum) RETURN COUNT(k) as count"
        count_result = neo4j_client.execute_query(count_query)
        total = count_result[0].get("count", 0) if count_result else 0
        
        return {
            "total": total,
            "skip": skip,
            "limit": limit,
            "concepts": [
                {
                    "nama": r.get("nama"),
                    "definisi": r.get("definisi"),
                    "frequency": r.get("frequency"),
                    "confidence": r.get("confidence"),
                }
                for r in results
            ]
        }
        
    except Exception as e:
        logger.error(f"List concepts failed: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to list concepts: {str(e)}"
        )


@router.get("/schema", tags=["graph"])
async def get_schema(neo4j_client = Depends(get_neo4j)):
    """Get graph schema information."""
    try:
        schema_info = neo4j_client.get_schema_info()
        
        return {
            "nodes": schema_info.get("labels", []),
            "relationships": schema_info.get("relationships", []),
            "indexes": schema_info.get("indexes", []),
            "constraints": schema_info.get("constraints", []),
        }
        
    except Exception as e:
        logger.error(f"Get schema failed: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get schema: {str(e)}"
        )


@router.get("/statistics", tags=["graph"])
async def get_statistics(neo4j_client = Depends(get_neo4j)):
    """Get graph statistics."""
    try:
        # Query node counts
        queries = {
            "peraturan": "MATCH (p:Peraturan) RETURN COUNT(p) as count",
            "pasal": "MATCH (p:Pasal) RETURN COUNT(p) as count",
            "ayat": "MATCH (a:Ayat) RETURN COUNT(a) as count",
            "konsep_hukum": "MATCH (k:KonsepHukum) RETURN COUNT(k) as count",
        }
        
        stats = {}
        
        for key, query in queries.items():
            result = neo4j_client.execute_query(query)
            stats[key] = result[0].get("count", 0) if result else 0
        
        return {
            "graph_statistics": stats,
            "timestamp": __import__('datetime').datetime.now().isoformat(),
        }
        
    except Exception as e:
        logger.error(f"Get statistics failed: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get statistics: {str(e)}"
        )
