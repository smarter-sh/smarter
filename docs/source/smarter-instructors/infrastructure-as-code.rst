Cloud Infrastructure as Code
============================

**Why Smarter.** The `smarter-infrastructure <https://github.com/smarter-sh/smarter-infrastructure>`__
repository builds Smarter's AWS environment with Terraform: the network, the Kubernetes cluster,
DNS, certificates, storage and email. Students can read a complete, real production configuration
without having to pay for one, and Smarter's own infrastructure service layer shows how an
application manages cloud resources at run time.

**Look at.** The ``smarter-infrastructure`` repository, and ``smarter/smarter/apps/infrastructure/``.

**Read.** :doc:`/smarter-platform/cloud-infrastructure`, :doc:`/smarter-framework/technologies/aws`,
:doc:`/smarter-framework/technologies/infrastructure`.

**Exercises.**

- Map each Terraform module to the AWS resources that it creates, and explain why the cluster sits
  on a private network.
- Run ``terraform plan`` against a sandbox AWS account, and estimate the monthly cost of the
  result. Compare it with the figures in :doc:`kubernetes`.
- Study how Smarter's infrastructure service layer lets the same code use AWS in production and a
  fake, in-memory provider in tests, and why that matters.

.. warning::

   ``terraform apply`` creates real, billable cloud resources. Use a dedicated sandbox account
   with a billing alert, and destroy what you create at the end of each session.

See the :doc:`Smarter Instructor Guide </smarter-instructor>` to install Smarter and set up
a class.
