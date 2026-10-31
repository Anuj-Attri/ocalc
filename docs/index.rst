ocalc
=====

``ocalc`` estimates the time and space complexity of a function. Paste a snippet on the `demo <demo.html>`_ and it reports the worst case in that file, or measure a Python function by running it.

.. code-block:: python

   # ocalc: Time: O(n); Space: O(1); Worst: 0.42 s at n=100000; Median: 0.31 s; Confidence: high; Protocol: min_n=100,max_n=100000,measures=8,budget=5,repeats=5
   def two_sum(nums, target):
       ...

The class is whichever of these formulas fits the measurements: ``1``, ``log n``, ``n``, ``n log n``, ``n^2``, ``n^3``, ``n^k``, ``c^n``. **Worst** is the slowest size that finished in this run, at that ``n``.

Run it again after a change. The next comment reuses the same sizes and keeps the old worst time as ``Previous``.

.. toctree::
   :maxdepth: 2
   :caption: Contents

   guide
   api
