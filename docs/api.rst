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


.. _evaluation:

Evaluation process
----

**HIGHLY EXPERIMENTAL API** - may soon change or disappear.

It is possible to start an evaluation process that compares the current process to another one, the reference process,
using the :meth:`averbis.Process.evaluate_against` method. Depending on the :class:`averbis.EvaluationConfiguration`, annotations of a specific type
are compared by selected features to each other. The comparison result is annotated as an evaluation annotation
e.g. a `TruePositive` annotation is created for an annotation if it matches the corresponding annotation in the reference process.
A `FalsePositive` is created, if the annotation exists in the current process, but not in the reference process.

During evaluation configuration, it is possible to distinguish between exact and partial matches. Annotations are marked
as an exact match if their type, features and position in the text are identical.
For a more fine-grained comparison than a hit or a miss, it is also possible to define a partial match.
Annotations that are not exactly identical, but still meet these criteria, are annotated as `PartialPositive`.

Starting an evaluation process for exact matches of `Diagnosis` annotations
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The given evaluation configuration describes an evaluation of diagnosis annotations by their begin and end features i.e.
two annotations match if they are Diagnosis annotations at the same position.

.. code:: python

  comparison_process = collection.get_process("process name")
  reference_process = collection.get_process("reference process name")

  diagnosis_config = EvaluationConfiguration(
        "de.averbis.types.health.Diagnosis",
        ["begin", "end"]
  )

  evaluation_process = comparison_process.evaluate_against(
    reference_process,
    "evaluation_of_diagnosis",
    [diagnosis_config]
  )

You can then query the state of the evaluation process until it is done and export text analysis results from it
using export methods from this API.


Trouble shooting the evaluation
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

If evaluation annotations are not created as expected, it might be that the annotation type
that has been configured for configuration is not an annotation that can stand alone but rather one
that is only referenced as a feature of other annotations (i.e. the annotation is not in the CAS index).
For this, it is not sufficient to adapt the evaluation configuration, but rather the annotation creation
has to be examined in the product.