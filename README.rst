Kinto signer
############

|travis| |coveralls|

.. |travis| image:: https://img.shields.io/github/workflow/status/Kinto/kinto-signer/test/master
    :target: https://github.com/Kinto/kinto-attachment/actions

.. |coveralls| image:: https://coveralls.io/repos/github/Kinto/kinto-signer/badge.svg?branch=master
    :target: https://coveralls.io/github/Kinto/kinto-signer?branch=master

**Kinto signer** is a `Kinto <https://kinto.readthedocs.io>`_ plugin
that signs records with a `content signature <https://github.com/mozilla-services/autograph/blob/e7c33d6/signer/contentsignature/README.rst>`_
to guarantee their integrity and authenticity.


How does it work?
=================

**Kinto signer** uses two collections:

* The *source*, where the authors create/update/delete records.
* The *destination*, where the clients obtain the records and their signature.

When the *source* collection metadata ``status`` is set to ``"to-sign"``, it will:

#. grab the whole list of records in this *source* collection
#. update the *destination* collection records with the recent changes
#. serialize the result in a Canonical JSON form (*see below*)
#. compute a signature using the configured backend
#. update the *destination* collection metadata ``signature`` with the information
   obtain form the signature backend
#. set the *source* metadata ``status`` to ``"signed"``.

A publishing workflow can be enabled (see below).

.. warning::

    The current implementation assumes the destination collection will be
    readable anonymously and won't be writable by anyone.
    (See `Kinto/kinto-signer#55 <https://github.com/Kinto/kinto-signer/issues/55>`_)


Content-Signature protocol
--------------------------

Kinto-signer produces signatures for the content of Kinto collections using
`ECDSA <https://fr.wikipedia.org/wiki/Elliptic_curve_digital_signature_algorithm>`_
with the P-384 strength.

* The content is prepended with ``Content-Signature:\x00`` prior to signing.
* The signature is produced with ECDSA on P-384 using SHA-384.
* The signature is returned as encoded using URL-safe variant of base-64.

See `Content Signature <https://github.com/mozilla-services/autograph/blob/e7c33d6/signer/contentsignature/README.rst>`_

The content signature is validated in Firefox using the `Personal Security Manager <https://developer.mozilla.org/en/docs/Mozilla/Projects/PSM>`_.


Notes on canonical JSON
-----------------------

The ``canonical_json()`` can be used in projects with:

.. code-block:: bash

    pip install --no-deps kinto-signer

.. code-block:: python

    from kinto_signer.serializer import canonical_json

Specific to Kinto:

* The payload to be signed has two attributes: ``last_modified`` with the
  current timestamp as a string, ``data`` with the array of records.
* Records are sorted by ascending ``id``
* Records with ``deleted: true`` are omitted

Standard canonical JSON:

* Object keys are sorted alphabetically
* No extra spaces in serialized content
* Double quotes are used
* Hexadecimal character escape sequences are used
* The alphabetical hexadecimal digits are lowercase
* Duplicate or empty properties are omitted
* ``NaN`` and ``Infinity`` are serialized as ``null``

About numbers:

* Scientific notation is used for numbers < 10e-6 and >= 10e21
* Exponents use a lowercase ``e`` and have no leading zeros
* Only significant numbers are kept (no fractional zeros)
* Float are serialized with 8 significant numbers at most

.. code-block:: python

    >>> canonical_json([{'id': '4', 'a': '"quoted"', 'b': 'Ich ♥ Bücher'},
                        {'id': '1', 'deleted': true},
                        {'id': '26', 'a': ''}])

    '[{"a":"","id":"26"},{"a":"\\"quoted\\"","b":"Ich \\u2665 B\\u00fccher","id":"4"}]'


* `Gecko client side code <https://searchfox.org/mozilla-central/rev/7c848ac7630df5baf1314b0c03e015683599efb9/toolkit/modules/CanonicalJSON.jsm>`_
* `ES6 Number#toString() <https://www.ecma-international.org/ecma-262/6.0/#sec-tostring-applied-to-the-number-type>`_ to obtain similar output for floats
* See `Internet-Draft Predictable Serialization for JSON Tools <https://tools.ietf.org/html/draft-rundgren-predictable-serialization-for-json-00>`_
* See `jsesc <https://github.com/mathiasbynens/jsesc>`_ to obtain similar output
  for escape sequences in JavaScript.


Setup
=====

To install this plugin in a Kinto server, a few configuration variables need
to be set.

Here is an example of what a configuration could look like:

.. code-block:: ini

  kinto.includes = kinto_signer

  kinto.signer.resources =
      /buckets/source                         -> /buckets/destination
      /buckets/source/collections/collection1 -> /buckets/destination/collections/collection2
      /buckets/bid/collections/cid            -> /buckets/bid/collections/cid2

+---------------------------------+--------------------------------------------------------------------------+
| Setting name                    | What does it do?                                                         |
+=================================+==========================================================================+
| kinto.signer.resources          | The source URIs (bucket or collection) on which signatures should be     |
|                                 | triggered and the destination where the data and the signatures will     |
|                                 | end-up.                                                                  |
|                                 |                                                                          |
|                                 | In the case buckets URIs are specified, every collection in the source   |
|                                 | bucket will be reviewed/signed, review and destination will keep the     |
|                                 | same id.                                                                 |
+---------------------------------+--------------------------------------------------------------------------+
| kinto.signer.signer_backend     | The python dotted location to the signer to use. By default, a local     |
|                                 | ECDSA signer will be used. Choices are either                            |
|                                 | ``kinto.signer.signer.local_ecdsa`` or ``kinto.signer.signer.autograph`` |
|                                 | Have a look at the sections below for more information.                  |
+---------------------------------+--------------------------------------------------------------------------+
| kinto.signer.allow_floats       | Allow float values in records (default: ``False``).                      |
|                                 | Toggling this setting to ``True`` can lead to signature verification     |
|                                 | errors in clients.                                                       |
|                                 | See ``kinto_signer.listeners.prevent_float_value``                       |
+---------------------------------+--------------------------------------------------------------------------+

Configuration for the (default) ECDSA local signer
--------------------------------------------------

+---------------------------------+--------------------------------------------------------------------------+
| Setting name                    | What does it do?                                                         |
+=================================+==========================================================================+
| kinto.signer.ecdsa.private_key  | Absolute path to the ECDSA private key to use to apply the signatures    |
+---------------------------------+--------------------------------------------------------------------------+
| kinto.signer.ecdsa.public_key   | Absolute path to the ECDSA private key to use to verify the signature    |
|                                 | (useful if you just want to use the signer as a verifier)                |
+---------------------------------+--------------------------------------------------------------------------+


Configuration for the Autograph signer
--------------------------------------

Kinto signer can integrate with the
`Autograph <https://github.com/mozilla-services/autograph>`_ server version 2.
To do so, use the following settings:

+------------------------------------+--------------------------------------------------------------------------+
| Setting name                       | What does it do?                                                         |
+====================================+==========================================================================+
| kinto.signer.autograph.server_url  | The autograph server URL                                                 |
+------------------------------------+--------------------------------------------------------------------------+
| kinto.signer.autograph.hawk_id     | The hawk identifier used to issue the requests.                          |
+------------------------------------+--------------------------------------------------------------------------+
| kinto.signer.autograph.hawk_secret | The hawk secret used to issue the requests.                              |
+------------------------------------+--------------------------------------------------------------------------+


Workflows
---------

A workflow can be enabled on the source collection ``status``.

The workflow is basically ``work-in-progress`` → ``to-review`` → ``to-sign`` → ``signed`` and
makes sure that:

* the collection is reviewed before being signed
* the user asking for review is the not the one approving the review
* the user asking for review belongs to a group ``editors`` and
  the one approving the review belongs to ``reviewers``.

+----------------------------------+---------------+--------------------------------------------------------------------------+
| Setting name                     | Default       | What does it do?                                                         |
+==================================+===============+==========================================================================+
| kinto.signer.to_review_enabled   | ``false``     | If ``true``, the collection ``status`` must be set to ``to-review`` by a |
|                                  |               | different user before being set to ``to-sign``.                          |
+----------------------------------+---------------+--------------------------------------------------------------------------+
| kinto.signer.group_check_enabled | ``false``     | If ``true``, the user setting to ``to-review`` must belong to the        |
|                                  |               | ``editors`` group in the source bucket, and the one setting to           |
|                                  |               | ``to-sign`` must belong to ``reviewers``.                                |
+----------------------------------+---------------+--------------------------------------------------------------------------+
| kinto.signer.editors_group       | ``editors``   | The group id that is required for changing status to ``to-review``       |
+----------------------------------+---------------+--------------------------------------------------------------------------+
| kinto.signer.reviewers_group     | ``reviewers`` | The group id that is required for changing status to ``to-sign``         |
+----------------------------------+---------------+--------------------------------------------------------------------------+

.. warning::

    The ``editors`` and ``reviewers`` groups are defined in the **source bucket**
    (e.g. ``/buckets/staging/groups/editors``).

    The ``editors`` and ``reviewers`` groups can have placeholders that are resolved
    with the source **source bucket/collection**
    (e.g. ``group:/buckets/{bucket_id}/groups/{collection_id}-reviewers``).

See `Kinto groups API <http://kinto.readthedocs.io/en/stable/api/1.x/groups.html>`_ for more details about how to define groups.

The above settings can be set or overriden by bucket using the ``<bucket_id>_`` prefix or by collection using the ``<bucket_id>_<collection_id>_`` prefix.
For example:

.. code-block:: ini

    kinto.signer.staging.group_check_enabled = true
    kinto.signer.staging.to_review_enabled = true
    kinto.signer.staging.certificates.group_check_enabled = false
    kinto.signer.staging.certificates.to_review_enabled = false
    kinto.signer.staging.certificates.reviewers_group = certificates-reviewers

If the review process is enabled, it is possible to configure a *preview*
collection, that will be updated and signed when the status is set to ``to-review``.
This *preview* collection can be used by clients to test and validate the changes
before approving them.

If a resources entry contains a semi-column separated **triplet**, then a preview
collection will be enabled.

.. code-block:: ini

  kinto.signer.resources =
      /buckets/staging            -> /buckets/preview            -> /buckets/blog
      /buckets/bid/collections/c1 -> /buckets/bid/collections/c2 -> /buckets/bid/collections/c3


.. image:: workflow.png


The editors and reviewers groups are automatically created when the source collection is created.


Multiple certificates
---------------------

Using above settings, every collections is signed with the same key.
But it is also possible to define multiple signers, per bucket or per collection.

Settings can be prefixed with bucket id:

.. code-block:: ini

    kinto.signer.signer_backend = kinto_signer.signer.autograph
    kinto.signer.autograph.server_url = http://172.11.20.1:8888

    kinto.signer.<bucket-id>.autograph.hawk_id = bob
    kinto.signer.<bucket-id>.autograph.hawk_secret = a-secret


Or prefixed with bucket and collection:

.. code-block:: ini

    kinto.signer.<bucket-id>.<collection-id>.signer_backend = kinto_signer.signer.local_ecdsa
    kinto.signer.<bucket-id>.<collection-id>.ecdsa.private_key = /path/to/private.pem
    kinto.signer.<bucket-id>.<collection-id>.ecdsa.public_key = /path/to/public.pem


Cloudfront CDN invalidation
---------------------------

When a request for review or approval is done, the changes are pushed to the preview
or destination collection.

For the setups where those public collections are served behind a Cloudfront CDN,
*kinto-signer* can take care of invalidating some paths.

.. code-block:: ini

    kinto.signer.distribution_id = E155JIFUEHFGY

By default, it invalidates the whole CDN (``/v1/*``). But paths can be configured:

.. code-block:: ini

    kinto.signer.invalidation_paths = /v1/buckets/{bucket_id}/collections/{collection_id}*
                                      /v1/buckets/monitor/collections/changes*
                                      /v1/blocklist/*

Usage
=====

Suppose we defined the following resources in the configuration:

.. code-block:: ini

    kinto.signer.resources = /buckets/source -> /buckets/destination

First, if necessary, we create the appropriate Kinto objects, for example, with ``httpie``:

.. code-block:: bash

    $ http PUT http://0.0.0.0:8888/v1/buckets/source --auth user:pass
    $ http PUT http://0.0.0.0:8888/v1/buckets/source/collections/collection1 --auth user:pass
    $ http PUT http://0.0.0.0:8888/v1/buckets/destination --auth user:pass
    $ http PUT http://0.0.0.0:8888/v1/buckets/destination/collections/collection1 --auth user:pass

Create some records in the *source* collection.

.. code-block:: bash

    $ echo '{"data": {"article": "title 1"}}' | http POST http://0.0.0.0:8888/v1/buckets/source/collections/collection1/records --auth user:pass
    $ echo '{"data": {"article": "title 2"}}' | http POST http://0.0.0.0:8888/v1/buckets/source/collections/collection1/records --auth user:pass


Trigger a signature operation, set the ``status`` field on the *source* collection metadata to ``"to-sign"``.

.. code-block:: bash

    echo '{"data": {"status": "to-sign"}}' | http PATCH http://0.0.0.0:8888/v1/buckets/source/collections/collection1 --auth user:pass

The *destination* collection should now contain the new records:

.. code-block:: bash

    $ http GET http://0.0.0.0:8888/v1/buckets/destination/collections/collection1/records --auth user:pass

.. code-block:: javascript

    {
        "data": [
            {
                "article": "title 2",
                "id": "a45c74a4-18c9-4bc2-bf0c-29d96badb9e6",
                "last_modified": 1460558489816
            },
            {
                "article": "title 1",
                "id": "f056f42b-3792-49f3-841d-0f637c7c6683",
                "last_modified": 1460558483981
            }
        ]
    }

The *destination* collection metadata now contains the signature:

.. code-block:: bash

   $ http GET http://0.0.0.0:8888/v1/buckets/destination/collections/collection1 --auth user:pass

.. code-block:: javascript

   {
       "data": {
           "id": "collection1",
           "last_modified": 1460558496510,
           "signature": {
               "mode": "p384ecdsa",
               "x5u": "https://bucket.example.net/appkey1.pem",
               "signature": "Nv-EJ1D0fanElBGP4ZZmV6zu_b4DuCP3H7xawlLrcR7to3aKzqfZknVXOi94G_w8-wdKlysVWmhuDMqJqPcJV7ZudbhypJpj7kllWdPvMRZkoWXSfYLaoLMc8VQEqZcb"
           }
       },
       "permissions": {
           "read": [
               "system.Everyone"
           ]
       }
   }

Tracking fields
---------------

During the review process, the *source* collection metadata will receive the following read-only fields:

- ``last_edit_by``: last user to perform change on records in the source collection
- ``last_edit_date``: date of the last records change
- ``last_review_request_by``: last user to request a review
- ``last_review_request_date``: date of the last review request
- ``last_review_by``: last user to approve a review
- ``last_review_date``: date of the last review approval
- ``last_signature_by``: last user to trigger a signature
- ``last_signature_date``: date of the last signature

.. note:

  ``last_signed_by`` can be different from ``last_review_by`` when the signature is refreshed
  (ie. status changed directly from ``signed`` to ``to-sign``).


Rollback changes
----------------

In order to reset the source (and preview) collection with the content of the destination collection (ie. last approved content), set the source to ``to-rollback``.

.. code-block:: bash

    echo '{"data": {"status": "to-rollback"}}' | http PATCH http://0.0.0.0:8888/v1/buckets/source/collections/collection1 --auth user:pass


Refresh signature
-----------------

In order to refresh the signature, set the source to ``to-resign``, the content signature
metadata will be recomputed and updated and the status restore to its previous value
(eg. ``signed`` or ``to-review``...).

This is useful when the signer certificates are rotated etc.

.. code-block:: bash

    echo '{"data": {"status": "to-resign"}}' | http PATCH http://0.0.0.0:8888/v1/buckets/source/collections/collection1 --auth user:pass


Events
======

Pyramid events are sent for each review step of the validation workflow.

Events have the following attributes:

* ``request``: current Pyramid request object
* ``payload``: same as ``kinto.core.events.ResourceChanged``
* ``impacted_records``: same as ``kinto.core.events.ResourceChanged``
* ``resource``: dict with details about source, preview and destination collection
                (as in capability).
* ``original_event``: original ``ResourceChanged`` event that was caught to
                      detect step change in review workflow.

The following events are thrown:

* ``kinto_signer.events.ReviewRequested``
* ``kinto_signer.events.ReviewRejected``
* ``kinto_signer.events.ReviewApproved``
* ``kinto_signer.events.ReviewCanceled`` (when source is rolledback)

.. important::

    The events are sent within the request's transaction. In other words, any
    database change that occurs in subscribers will be committed or rolledback
    depending of the overall response status.


Validating the signature
========================

With `kinto.js <https://github.com/Kinto/kinto.js/>`_, it is possible to define
incoming hooks that are executed when the data is retrieved from the server.

.. code-block:: javascript

    const kinto = new Kinto({
      remote: "https://mykinto.com/v1",
      bucket: "a-bucket"
    });
    const collection = kinto.collection("a-collection", {
      hooks: {
        "incoming-changes": [validateCollectionSignature]
      }});

.. code-block:: javascript

    function validateCollectionSignature(payload, collection) {
      // 1 - Fetch signature from collection endpoint
      // 2 - Fetch public key certificate
      // 3 - Merge incoming changes with local records
      // 4 - Serialize as canonical JSON
      // 5 - Verify the signature against the content with the public key
      // 6 - Return `payload` if valid, throw error otherwise.
    }

The content of the ``demo/`` folder implements the signature verification with
kinto.js and the WebCrypto API. It is `published online <https://kinto.github.io/kinto-signer/>`_
but relies on a semi-public server instance.

See also `the complete integration within Firefox <https://bugzilla.mozilla.org/show_bug.cgi?id=1263602>`_
using the `Network Security Services <https://developer.mozilla.org/en-US/docs/Mozilla/Projects/NSS/Overview>`_.


Generating a keypair
====================

To generate a new keypair, you can use the following command::

  $ python -m kinto_signer.generate_keypair private.pem public.pem


Running the tests
=================

In order to contribute and run the full functional test suite locally you need
to have the Go language executables (e.g. `sudo apt-get install golang`)
and a ``testdb`` PostgreSQL database like for the Kinto server.

The rest of installation and setup process is taken care of automatically.

To run the unit tests::

  $ make tests

For the functional tests, run these two services in separate terminals:

::

  $ make run-kinto

::

  $ make run-autograph

And start the test suite::

  $ make functional
