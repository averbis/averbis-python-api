.. _api:

API Reference
=============

.. automodule:: averbis
    :members:
    :undoc-members:
    :exclude-members: Client

.. autoclass:: averbis.Client
   :members:
   :inherited-members:
   :special-members: __init__

.. _UIMA types:

Supported UIMA File Types
----

The supported file content types (mime_types) are

- UIMA CAS XMI (application/vnd.uima.cas+xmi)
- XCAS (application/vnd.uima.cas+xcas)
- binary CAS (application/vnd.uima.cas+binary)
- binary TSI (application/vnd.uima.cas+binary.tsi)
- compressed (application/vnd.uima.cas+compressed)
- compressed TSI (application/vnd.uima.cas+compressed.tsi)
- compressed filtered (application/vnd.uima.cas+compressed.filtered)
- compressed filtered TS (application/vnd.uima.cas+compressed.filtered.ts)
- compressed filtered TSI (application/vnd.uima.cas+compressed.filtered.tsi)
- serialized CAS (application/vnd.uima.cas+serialized)
- serialized TSI (application/vnd.uima.cas+serialized.tsi)
