__all__ = ["app"]


def __getattr__(name: str):
	if name == "app":
		from gigai.main import app

		return app
	raise AttributeError(f"module 'gigai' has no attribute '{name}'")
