from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
import os
from .routers.dids import router as dids_router
from .routers.vcs import router as vcs_router
from .routers.oac import router as oac_router
from .routers.variables import router as variables_router
from .routers.groups import router as groups_router
from .routers.croissants import router as croissants_router
from .routers.registry import router as registry_router

app = FastAPI(title="ODRL API", description="API wrapper for OYDID CLI with VC Capabilities")

# API Routers with /api prefix
app.include_router(dids_router, prefix="/api")
app.include_router(vcs_router, prefix="/api")
app.include_router(oac_router, prefix="/api")
app.include_router(variables_router, prefix="/api")
app.include_router(groups_router, prefix="/api")
app.include_router(croissants_router, prefix="/api")
app.include_router(registry_router, prefix="/api")

@app.get("/api/health")
async def health_check():
    return {"status": "ok", "service": "oydid-api"}

@app.get("/api/oydid/health")
async def oydid_health():
    from .services.oydid import run_oydid_command
    import json
    try:
        result = run_oydid_command(["--version"])
        return {
            "status": "ok" if result.returncode == 0 else "error",
            "returncode": result.returncode,
            "stdout": result.stdout.strip(),
            "stderr": result.stderr.strip()
        }
    except Exception as e:
        return {"status": "error", "detail": str(e)}

# Serve Frontend Static Files
# Priority 1: Docker build location (outside bind mount)
docker_static_dir = "/frontend_dist"
# Priority 2: Local development location
local_static_dir = os.path.join(os.path.dirname(__file__), "static")

if os.path.exists(docker_static_dir):
    static_dir = docker_static_dir
    app.mount("/", StaticFiles(directory=static_dir, html=True), name="static")
elif os.path.exists(local_static_dir):
    static_dir = local_static_dir
    app.mount("/", StaticFiles(directory=static_dir, html=True), name="static")
else:
    static_dir = None
    print("Warning: Static files not found")

def get_index_html():
    """Return the index.html path from whichever static dir is available."""
    if os.path.exists(docker_static_dir):
        index = os.path.join(docker_static_dir, "index.html")
    elif os.path.exists(local_static_dir):
        index = os.path.join(local_static_dir, "index.html")
    else:
        return None
    return index if os.path.exists(index) else None

# Explicit SPA routes — these must be declared BEFORE the static mount catch-all
# so the server returns 200 + index.html instead of 502/404 for client-side routes.
SPA_ROUTES = [
    "/auth/{provider}/callback",
    "/dids",
    "/vcs",
    "/policies",
    "/prompts",
    "/variables",
    "/croissants",
    "/groups",
    "/demo",
    "/profile",
]

for _route in SPA_ROUTES:
    @app.get(_route, include_in_schema=False)
    async def _spa_route():
        index = get_index_html()
        if index:
            return FileResponse(index)
        return JSONResponse(status_code=503, content={"detail": "Frontend not built"})

# Catch-all route for SPA (React Router)
@app.exception_handler(404)
async def custom_404_handler(request, __):
    if request.url.path.startswith("/api"):
        return JSONResponse(status_code=404, content={"detail": "Not Found"})

    index = get_index_html()
    if index:
        return FileResponse(index)
    return JSONResponse(status_code=404, content={"detail": "Not Found"})
