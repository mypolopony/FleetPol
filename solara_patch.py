import solara.server.server as solara_server

def patched_get_nbextensions():
    try:
        from solara.server import jupytertools
        paths = jupytertools.get_nb_paths()
        config = jupytertools.get_config(paths, "notebook")
        return config.get("load_extensions", {}), {}
    except Exception:
        return {}, {}

solara_server.get_nbextensions = patched_get_nbextensions