# vectorstore

- Support for locally-hosted vector databases, including support for mixed
  mode storage with MariaDB as the persistence store for metadata.
- CRUD operations on vector database stores with emphasis on loading and
  querying a database.

## Register New Vectorstore

1. add to .enum.SmarterVectorStoreBackends
2. add to .models.VectorDatabaseBackendKind
3. add to .backends.Backends._backends
4. create a new class in .backends that descends from SmarterVectorstoreBackend
