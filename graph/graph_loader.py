"""
Graph Loader - Load enriched content into Neo4j

Transforms output from TAHAP 2 (enriched_content.json) into Neo4j graph.
Creates nodes for Peraturan, Pasal, Ayat, KonsepHukum
Creates relationships: BAGIAN_DARI, MERUJUK_KE, MENGATUR, etc.
"""

import json
from pathlib import Path
from typing import List, Dict, Any, Tuple
from datetime import datetime
from dataclasses import dataclass

from graph.neo4j_client import Neo4jClient
from ingestion.models import PDFExtractedContent
from extraction.models import EnrichedDocumentContent
from ingestion.utils import get_logger


logger = get_logger("legalkg.graph_loader")


@dataclass
class LoaderConfig:
    """Configuration for graph loading."""
    batch_size: int = 500
    skip_existing: bool = False
    create_indexes: bool = True
    generate_embeddings: bool = False  # For TAHAP 4


class GraphLoader:
    """Load enriched content into Neo4j graph."""
    
    def __init__(self, neo4j_client: Neo4jClient, config: LoaderConfig = None):
        """
        Initialize graph loader.
        
        Args:
            neo4j_client: Connected Neo4j client
            config: Loader configuration
        """
        self.neo4j = neo4j_client
        self.config = config or LoaderConfig()
        self.stats = {
            "peraturan_created": 0,
            "pasal_created": 0,
            "ayat_created": 0,
            "konsep_created": 0,
            "relationships_created": 0,
            "failed_items": 0,
        }
    
    def load_enriched_documents(self, enriched_docs: List[EnrichedDocumentContent]) -> Dict[str, Any]:
        """
        Load enriched documents into graph.
        
        Args:
            enriched_docs: List of enriched documents from TAHAP 2
            
        Returns:
            Loading statistics
        """
        logger.info(f"🔄 Loading {len(enriched_docs)} enriched documents into Neo4j...")
        
        total_start = datetime.now()
        
        for idx, doc in enumerate(enriched_docs):
            logger.info(f"  [{idx+1}/{len(enriched_docs)}] Loading {doc.nomor_peraturan}...")
            
            try:
                # 1. Create Peraturan node
                self._create_peraturan_node(doc)
                
                # 2. Create Pasal + Ayat nodes with BAGIAN_DARI relationships
                self._create_pasal_and_ayat_nodes(doc)
                
                # 3. Create inter-pasal MERUJUK_KE relationships
                self._create_pasal_references(doc)
                
                # 4. Create KonsepHukum nodes and MENGATUR relationships
                self._create_konsep_hukum_nodes(doc)
                
            except Exception as e:
                logger.error(f"❌ Failed to load {doc.nomor_peraturan}: {e}")
                self.stats["failed_items"] += 1
        
        total_duration = (datetime.now() - total_start).total_seconds()
        self.stats["duration_seconds"] = total_duration
        
        logger.info(f"\n✅ Loading complete in {total_duration:.1f}s")
        logger.info(f"  Peraturan: {self.stats['peraturan_created']}")
        logger.info(f"  Pasal: {self.stats['pasal_created']}")
        logger.info(f"  Ayat: {self.stats['ayat_created']}")
        logger.info(f"  KonsepHukum: {self.stats['konsep_created']}")
        logger.info(f"  Relationships: {self.stats['relationships_created']}")
        
        return self.stats
    
    def _create_peraturan_node(self, doc: EnrichedDocumentContent) -> None:
        """Create Peraturan node."""
        query = """
        MERGE (p:Peraturan {id: $id})
        SET p += {
            nomor: $nomor,
            judul: $judul,
            tahun: $tahun,
            jenis: $jenis,
            lembaga_penerbit: $lembaga_penerbit,
            tanggal_disahkan: $tanggal_disahkan,
            tanggal_diundangkan: $tanggal_diundangkan,
            created_at: $created_at,
            updated_at: $updated_at,
            source: 'BPK Crawler',
            total_pasal: $total_pasal,
            total_entities: $total_entities,
            total_references: $total_references,
            total_konsep: $total_konsep
        }
        """
        
        # Extract metadata (from first enriched pasal if available)
        params = {
            "id": doc.nomor_peraturan.replace(" ", "_"),
            "nomor": doc.nomor_peraturan,
            "judul": getattr(doc, "judul", ""),
            "tahun": getattr(doc, "tahun", None),
            "jenis": getattr(doc, "jenis", ""),
            "lembaga_penerbit": getattr(doc, "lembaga_penerbit", ""),
            "tanggal_disahkan": getattr(doc, "tanggal_disahkan", None),
            "tanggal_diundangkan": getattr(doc, "tanggal_diundangkan", None),
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
            "total_pasal": len(doc.enriched_pasals),
            "total_entities": len(doc.all_entities),
            "total_references": len(doc.all_references),
            "total_konsep": len(doc.konsep_hukum_list),
        }
        
        result = self.neo4j.execute_write_transaction(query, params)
        if result.get("success"):
            self.stats["peraturan_created"] += 1
    
    def _create_pasal_and_ayat_nodes(self, doc: EnrichedDocumentContent) -> None:
        """Create Pasal + Ayat nodes with BAGIAN_DARI relationships."""
        
        for pasal in doc.enriched_pasals:
            # Create Pasal node
            pasal_id = f"{doc.nomor_peraturan}__Pasal_{pasal.nomor_pasal}".replace(" ", "_")
            
            query = """
            MERGE (p:Pasal {id: $pasal_id})
            SET p += {
                nomor: $nomor,
                judul: $judul,
                full_text: $full_text,
                created_at: $created_at,
                source: 'PDF Extraction',
                ayat_count: size($ayat_keys),
                entity_count: $entity_count,
                reference_count: $reference_count
            }
            """
            
            ayat_keys = list(pasal.ayat.keys()) if pasal.ayat else []
            
            result = self.neo4j.execute_write_transaction(
                query,
                {
                    "pasal_id": pasal_id,
                    "nomor": pasal.nomor_pasal,
                    "judul": getattr(pasal, "judul", ""),
                    "full_text": pasal.full_text or "",
                    "created_at": datetime.now().isoformat(),
                    "ayat_keys": ayat_keys,
                    "entity_count": len(pasal.entities),
                    "reference_count": len(pasal.references),
                }
            )
            
            if result.get("success"):
                self.stats["pasal_created"] += 1
            
            # Create BAGIAN_DARI relationship (Pasal -> Peraturan)
            self._create_bagian_dari_relationship(
                pasal_id,
                doc.nomor_peraturan,
                "Pasal",
            )
            
            # Create Ayat nodes if present
            if pasal.ayat:
                for ayat_nomor, ayat_text in pasal.ayat.items():
                    ayat_id = f"{pasal_id}__Ayat_{ayat_nomor}".replace(" ", "_")
                    
                    query = """
                    MERGE (a:Ayat {id: $ayat_id})
                    SET a += {
                        nomor: $nomor,
                        text: $text,
                        created_at: $created_at
                    }
                    """
                    
                    result = self.neo4j.execute_write_transaction(
                        query,
                        {
                            "ayat_id": ayat_id,
                            "nomor": ayat_nomor,
                            "text": ayat_text or "",
                            "created_at": datetime.now().isoformat(),
                        }
                    )
                    
                    if result.get("success"):
                        self.stats["ayat_created"] += 1
                    
                    # Create BAGIAN_DARI relationship (Ayat -> Pasal)
                    self._create_bagian_dari_relationship(
                        ayat_id,
                        pasal_id,
                        "Ayat",
                    )
    
    def _create_bagian_dari_relationship(
        self,
        source_id: str,
        target_id: str,
        source_type: str,
    ) -> None:
        """Create BAGIAN_DARI relationship."""
        query = """
        MATCH (source {id: $source_id}), (target {id: $target_id})
        MERGE (source)-[r:BAGIAN_DARI]->(target)
        SET r.created_at = $created_at
        """
        
        result = self.neo4j.execute_write_transaction(
            query,
            {
                "source_id": source_id,
                "target_id": target_id,
                "created_at": datetime.now().isoformat(),
            }
        )
        
        if result.get("success"):
            self.stats["relationships_created"] += 1
    
    def _create_pasal_references(self, doc: EnrichedDocumentContent) -> None:
        """Create inter-pasal MERUJUK_KE relationships."""
        
        for pasal in doc.enriched_pasals:
            for reference in pasal.references:
                source_pasal_id = f"{doc.nomor_peraturan}__Pasal_{reference.source_pasal}".replace(" ", "_")
                target_pasal_id = f"{doc.nomor_peraturan}__Pasal_{reference.target_pasal}".replace(" ", "_")
                
                query = """
                MATCH (source {id: $source_id}), (target {id: $target_id})
                MERGE (source)-[r:MERUJUK_KE]->(target)
                SET r += {
                    type: $type,
                    reference_text: $reference_text,
                    confidence: $confidence,
                    created_at: $created_at
                }
                """
                
                result = self.neo4j.execute_write_transaction(
                    query,
                    {
                        "source_id": source_pasal_id,
                        "target_id": target_pasal_id,
                        "type": reference.reference_type,
                        "reference_text": reference.reference_text,
                        "confidence": reference.confidence,
                        "created_at": datetime.now().isoformat(),
                    }
                )
                
                if result.get("success"):
                    self.stats["relationships_created"] += 1
    
    def _create_konsep_hukum_nodes(self, doc: EnrichedDocumentContent) -> None:
        """Create KonsepHukum nodes and MENGATUR relationships."""
        
        for konsep in doc.konsep_hukum_list:
            # Create KonsepHukum node
            konsep_id = konsep.nama.replace(" ", "_").lower()
            
            query = """
            MERGE (k:KonsepHukum {id: $konsep_id})
            SET k += {
                nama: $nama,
                definisi: $definisi,
                pasal_utama: $pasal_utama,
                frequency: $frequency,
                confidence: $confidence,
                terkait_pasals: $terkait_pasals,
                created_at: $created_at
            }
            """
            
            result = self.neo4j.execute_write_transaction(
                query,
                {
                    "konsep_id": konsep_id,
                    "nama": konsep.nama,
                    "definisi": getattr(konsep, "definisi", ""),
                    "pasal_utama": konsep.pasal_utama,
                    "frequency": konsep.frequency,
                    "confidence": konsep.confidence,
                    "terkait_pasals": getattr(konsep, "terkait_pasals", []),
                    "created_at": datetime.now().isoformat(),
                }
            )
            
            if result.get("success"):
                self.stats["konsep_created"] += 1
            
            # Create MENGATUR relationship (Pasal -> KonsepHukum)
            pasal_id = f"{doc.nomor_peraturan}__Pasal_{konsep.pasal_utama}".replace(" ", "_")
            
            query = """
            MATCH (pasal {id: $pasal_id}), (konsep {id: $konsep_id})
            MERGE (pasal)-[r:MENGATUR]->(konsep)
            SET r.confidence = $confidence,
                r.created_at = $created_at
            """
            
            result = self.neo4j.execute_write_transaction(
                query,
                {
                    "pasal_id": pasal_id,
                    "konsep_id": konsep_id,
                    "confidence": konsep.confidence,
                    "created_at": datetime.now().isoformat(),
                }
            )
            
            if result.get("success"):
                self.stats["relationships_created"] += 1
    
    def load_from_json_file(self, json_file: str) -> Dict[str, Any]:
        """
        Load from enriched_content.json file.
        
        Args:
            json_file: Path to enriched_content.json from TAHAP 2
            
        Returns:
            Loading statistics
        """
        logger.info(f"📂 Loading from {json_file}...")
        
        try:
            with open(json_file) as f:
                data = json.load(f)
            
            # Convert dicts to EnrichedDocumentContent objects
            enriched_docs = []
            for item in data:
                doc = EnrichedDocumentContent(**item)
                enriched_docs.append(doc)
            
            return self.load_enriched_documents(enriched_docs)
        
        except Exception as e:
            logger.error(f"❌ Failed to load from JSON: {e}")
            return {"error": str(e)}
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get loading statistics."""
        return self.stats.copy()
