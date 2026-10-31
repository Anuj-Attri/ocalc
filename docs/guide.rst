Guide
=====

Install
-------

From GitHub:

.. code-block:: bash

   pip install "git+https://github.com/Anuj-Attri/ocalc.git"

From a checkout:

.. code-block:: bash

   pip install -e .

The core package depends on NumPy. The editor tools are optional:

.. code-block:: bash

   pip install -e ".[mcp]"

Command line
------------

.. code-block:: bash

   ocalc measure FILE -f two_sum --sample "[1, 2, 3], 9"
   ocalc annotate FILE -f two_sum --sample "[1, 2, 3], 9"

``measure`` prints the size table and the comment. ``annotate`` writes the comment above the function and replaces an older ocalc comment. You ask, then the tool runs.

Protocol flags, with their defaults:

.. code-block:: bash

   ocalc measure FILE -f two_sum --sample "[1, 2, 3], 9" --min-n 100 --max-n 20000 --measures 6 --budget 3 --repeats 3

``--budget`` is seconds to spend (5). ``--min-n`` and ``--max-n`` are the size grid (100 and 100000, or 8 and 100000 when the only input is an int). ``--measures`` is how many sizes to try (8). ``--repeats`` is how many timed calls to make at each size (5). A later annotate reuses the protocol stored in the comment unless you pass a flag.

The first list, tuple, set, dict, or bytes argument grows with ``n``. A lone string grows when it is the input. A single int, as in ``fib(n)``, is ``n``. Other arguments stay at the sample or the type hint. Keyword arguments are written ``factor=3``. A sample that does not match a hint is not forced into that parameter: ``add(nums: list[int], b: int)`` with ``--sample "1, 9"`` still grows a list and keeps an int.

``--sample`` accepts Python literals. A function with nothing to grow is called as written and reported as ``O(1)``. Methods are measured when the class can be constructed with no arguments. ``async def`` functions are awaited.

A list of numbers becomes ``0 .. n-1``. A sample of records, such as a list of dicts, is copied until it has ``n`` items, and each copy keeps the sample's keys and nested values. A file inside a package is imported as that package, so relative imports keep working. Code under ``if __name__ == "__main__"`` does not run.

Python
------

.. code-block:: python

   from ocalc import measure

   def two_sum(nums: list, target: int):
       seen = {}
       for index, value in enumerate(nums):
           if target - value in seen:
               return [seen[target - value], index]
           seen[value] = index
       return []

   report = measure(two_sum, [1, 2, 3], 9)
   print(report.comment)

Type hints are enough when they say what to grow. ``list``, ``set``, and ``dict`` plus an ``int`` grow the collection and keep the int fixed. A single ``int`` argument, as in ``fib(n)``, is the size. Two plain ints are called as given. Pass ``repeats=``, ``min_n=``, ``max_n=``, ``measures=``, and ``budget=`` to ``measure`` to change the protocol.

Editor tools
------------

Install the extra, then add this to the project MCP config:

.. code-block:: json

   {
     "mcpServers": {
       "ocalc": {
         "command": "ocalc",
         "args": ["mcp"]
       }
     }
   }

The server exposes ``measure_function`` and ``annotate_function``.

What the numbers mean
---------------------

The benchmark builds each input before the timer starts. It takes the median of a few calls at each size and records the ``tracemalloc`` peak of one call.

Confidence is high, medium, low, or inconclusive. Low names the runner-up class. Inconclusive means too few sizes finished, or none of the formulas fit.
