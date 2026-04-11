Smarter VectorStore
=====================

Smarter VectorStore is a Django application that provides a framework for managing vector stores
from a variety of vendors, running both locally and in the cloud. It is designed for ease of
use and flexibility. It is fully integrated into the Smarter Framework, namely the
:doc:`Smarter Application Manifest (SAM) <smarter-manifests>` yaml manifest-based API.

The Smarter Vectorstore Django app provides a robust service layer for managing
vector databases, abstracting the complexities of provisioning, deleting, and
interacting with various vector store backends. At its core is the
:doc:`VectorstoreService <smarter-vectorstore/services>` class, which acts as a
bridge between the ORM model (:doc:`VectorDatabase <smarter-vectorstore/models>`)
and the backend implementations that handle the actual
storage and retrieval of vector data. This service is designed to be
backend-agnostic, allowing seamless integration with different vector store
technologies by encapsulating backend logic (see :doc:`VectorstoreBackend <smarter-vectorstore/backends>`)
and exposing a consistent interface for higher-level operations.
It also tightly integrates with :doc:`LLM provider models <smarter-provider>`
and embedding services, ensuring that the process of generating and storing
embeddings is both modular and extensible.

The module emphasizes operational readiness and logging, using feature
flags (:doc:`waffle switches <smarter-waffle>`) to control logging behavior and providing detailed debug
information throughout its methods. It supports advanced document processing
workflows, such as loading and embedding PDF documents, by leveraging tools like
PyPDFLoader and RecursiveCharacterTextSplitter to split documents into manageable
chunks and generate embeddings for each. These embeddings are then stored in the
vector database via the backend, enabling efficient similarity search and retrieval.
Overall, the Smarter Vectorstore app is architected to provide a scalable, maintainable,
and extensible foundation for vector-based data operations within a Django environment,
supporting a wide range of use cases from document search to AI-powered applications.

.. toctree::
   :maxdepth: 1
   :caption: Technical Reference

   smarter-vectorstore/backends
   smarter-vectorstore/models
   smarter-vectorstore/receivers
   smarter-vectorstore/serializers
   smarter-vectorstore/services
   smarter-vectorstore/signals
   smarter-vectorstore/tasks
