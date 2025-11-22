from src.data import schema, loader
from src.core import batching, analysis, reporting, validation
from src.core.optimization import model, heuristic, solver
from src.visualization import gantt

if __name__ == "__main__":
    schema.run()
    loader.run()
    batching.run()
    model.run()
    heuristic.run()
    analysis.run()
    solver.run()
    validation.run()
    gantt.run()