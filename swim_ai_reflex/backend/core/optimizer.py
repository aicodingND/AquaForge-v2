"""
DEPRECATED: This module is kept for backward compatibility.
Please use swim_ai_reflex.backend.core.optimizer_factory and strategies instead.
"""

# For backward compatibility, we can expose simple wrappers around the strategies
# if absolutely needed, but for now we just expose the Utils.
# The original optimization functions (optimize_global_seton, optimize_with_gurobi) 
# are complex to re-export perfectly without cyclic imports or duplicating logic wrappers.
# Since we updated the only known consumer (OptimizationService), we will leave them out 
# to encourage moving to the Factory.

def optimize_global_seton(*args, **kwargs):
    raise DeprecationWarning("optimize_global_seton is deprecated. Use OptimizerFactory.get_strategy('heuristic')")

def optimize_with_gurobi(*args, **kwargs):
    raise DeprecationWarning("optimize_with_gurobi is deprecated. Use OptimizerFactory.get_strategy('gurobi')")