// LegalKG - Neo4j Graph Schema Definition
// TAHAP 3: Graph Configuration
// Author: LegalKG Team
// Version: 1.0.0

// ============================================================================
// NODE LABELS & CONSTRAINTS
// ============================================================================

// PERATURAN (Regulation/Legislation)
// ============================================================================
CREATE CONSTRAINT peraturan_id IF NOT EXISTS 
  FOR (p:Peraturan) REQUIRE p.id IS UNIQUE;
CREATE CONSTRAINT peraturan_nomor IF NOT EXISTS
  FOR (p:Peraturan) REQUIRE p.nomor IS UNIQUE;

CREATE INDEX idx_peraturan_tahun IF NOT EXISTS 
  FOR (p:Peraturan) ON (p.tahun);
CREATE INDEX idx_peraturan_jenis IF NOT EXISTS
  FOR (p:Peraturan) ON (p.jenis);
CREATE INDEX idx_peraturan_lembaga IF NOT EXISTS
  FOR (p:Peraturan) ON (p.lembaga_penerbit);

// PASAL (Article within Regulation)
// ============================================================================
CREATE CONSTRAINT pasal_id IF NOT EXISTS
  FOR (p:Pasal) REQUIRE p.id IS UNIQUE;

CREATE INDEX idx_pasal_nomor IF NOT EXISTS
  FOR (p:Pasal) ON (p.nomor);
CREATE INDEX idx_pasal_judul IF NOT EXISTS
  FOR (p:Pasal) ON (p.judul);

// AYAT (Clause within Article)
// ============================================================================
CREATE CONSTRAINT ayat_id IF NOT EXISTS
  FOR (a:Ayat) REQUIRE a.id IS UNIQUE;

CREATE INDEX idx_ayat_nomor IF NOT EXISTS
  FOR (a:Ayat) ON (a.nomor);

// LEMBAGA (Institution/Agency)
// ============================================================================
CREATE CONSTRAINT lembaga_id IF NOT EXISTS
  FOR (l:Lembaga) REQUIRE l.id IS UNIQUE;
CREATE CONSTRAINT lembaga_nama IF NOT EXISTS
  FOR (l:Lembaga) REQUIRE l.nama IS UNIQUE;

CREATE INDEX idx_lembaga_nama IF NOT EXISTS
  FOR (l:Lembaga) ON (l.nama);

// KONSEP_HUKUM (Legal Concept/Term)
// ============================================================================
CREATE CONSTRAINT konsep_id IF NOT EXISTS
  FOR (k:KonsepHukum) REQUIRE k.id IS UNIQUE;
CREATE CONSTRAINT konsep_nama IF NOT EXISTS
  FOR (k:KonsepHukum) REQUIRE k.nama IS UNIQUE;

CREATE INDEX idx_konsep_nama IF NOT EXISTS
  FOR (k:KonsepHukum) ON (k.nama);
CREATE INDEX idx_konsep_frequency IF NOT EXISTS
  FOR (k:KonsepHukum) ON (k.frequency);
CREATE INDEX idx_konsep_confidence IF NOT EXISTS
  FOR (k:KonsepHukum) ON (k.confidence);

// ============================================================================
// RELATIONSHIP TYPES & CONSTRAINTS
// ============================================================================

// STRUCTURAL RELATIONSHIPS
// ============================================================================
// BAGIAN_DARI (Ayat -> Pasal -> Peraturan)
CREATE INDEX idx_rel_bagian_dari IF NOT EXISTS
  FOR ()-[r:BAGIAN_DARI]-() ON (r.order_index);

// MERUJUK_KE (Pasal -> Pasal) - Inter-pasal references
// ============================================================================
CREATE INDEX idx_rel_merujuk_ke IF NOT EXISTS
  FOR ()-[r:MERUJUK_KE]-() ON (r.confidence);

// MENGATUR (Pasal -> KonsepHukum)
// ============================================================================
CREATE INDEX idx_rel_mengatur IF NOT EXISTS
  FOR ()-[r:MENGATUR]-() ON (r.confidence);

// TEMPORAL RELATIONSHIPS
// ============================================================================
// MENCABUT / DICABUT_OLEH (Peraturan -> Peraturan)
// ============================================================================
CREATE INDEX idx_rel_mencabut IF NOT EXISTS
  FOR ()-[r:MENCABUT]-() ON (r.tanggal);

// MENGUBAH / DIUBAH_OLEH (Peraturan -> Peraturan)
// ============================================================================
CREATE INDEX idx_rel_mengubah IF NOT EXISTS
  FOR ()-[r:MENGUBAH]-() ON (r.tanggal);

// DASAR_DELEGASI (Peraturan -> Peraturan) - Hierarchical delegation
// ============================================================================
CREATE INDEX idx_rel_dasar_delegasi IF NOT EXISTS
  FOR ()-[r:DASAR_DELEGASI]-() ON (r.order_index);

// PENERBIT_OLEH (Peraturan -> Lembaga)
// ============================================================================
// (No special index needed - limited relationships)

// TERKAIT_DENGAN (KonsepHukum -> KonsepHukum) - Semantic links
// ============================================================================
CREATE INDEX idx_rel_terkait_dengan IF NOT EXISTS
  FOR ()-[r:TERKAIT_DENGAN]-() ON (r.confidence);

// ============================================================================
// VECTOR INDEXES (For Semantic Search)
// ============================================================================

// Vector index untuk Pasal (text-embedding-3-small: 1536 dimensions)
// ============================================================================
CREATE VECTOR INDEX idx_pasal_embedding IF NOT EXISTS
  FOR (p:Pasal) ON (p.embedding)
  OPTIONS {
    indexConfig: {
      `vector.dimensions`: 1536,
      `vector.similarity_metric`: 'cosine'
    }
  };

// Vector index untuk KonsepHukum
// ============================================================================
CREATE VECTOR INDEX idx_konsep_embedding IF NOT EXISTS
  FOR (k:KonsepHukum) ON (k.embedding)
  OPTIONS {
    indexConfig: {
      `vector.dimensions`: 1536,
      `vector.similarity_metric`: 'cosine'
    }
  };

// Vector index untuk Peraturan (full text)
// ============================================================================
CREATE VECTOR INDEX idx_peraturan_embedding IF NOT EXISTS
  FOR (p:Peraturan) ON (p.embedding)
  OPTIONS {
    indexConfig: {
      `vector.dimensions`: 1536,
      `vector.similarity_metric`: 'cosine'
    }
  };

// ============================================================================
// FULL-TEXT SEARCH INDEXES
// ============================================================================

CREATE FULLTEXT INDEX idx_pasal_search IF NOT EXISTS
  FOR (p:Pasal) ON EACH [p.judul, p.full_text];

CREATE FULLTEXT INDEX idx_konsep_search IF NOT EXISTS
  FOR (k:KonsepHukum) ON EACH [k.nama, k.definisi];

CREATE FULLTEXT INDEX idx_peraturan_search IF NOT EXISTS
  FOR (p:Peraturan) ON EACH [p.judul, p.nomor];

// ============================================================================
// PROPERTY CONSTRAINTS
// ============================================================================

// Ensure timestamps are valid
CREATE CONSTRAINT created_at_exists IF NOT EXISTS
  FOR (n:Peraturan|Pasal|KonsepHukum) REQUIRE n.created_at IS NOT NULL;

// Ensure relationships have confidence scores where applicable
CREATE CONSTRAINT reference_confidence IF NOT EXISTS
  FOR ()-[r:MERUJUK_KE]-() REQUIRE r.confidence IS NOT NULL;

CREATE CONSTRAINT entity_confidence IF NOT EXISTS
  FOR ()-[r:MENGATUR]-() REQUIRE r.confidence IS NOT NULL;

// ============================================================================
// VERIFICATION QUERIES (Run after schema setup)
// ============================================================================

// Check constraints created
// SHOW CONSTRAINTS;

// Check indexes created
// SHOW INDEXES;

// Get database statistics
// CALL db.stats.retrieve('nodes');
// CALL db.stats.retrieve('relationships');

// ============================================================================
// SCHEMA END
// ============================================================================
