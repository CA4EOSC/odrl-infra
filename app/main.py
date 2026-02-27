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

app = FastAPI(title="ODRL API", description="API wrapper for OYDID CLI with VC Capabilities")

# API Routers with /api prefix
app.include_router(dids_router, prefix="/api")
app.include_router(vcs_router, prefix="/api")
app.include_router(oac_router, prefix="/api")
app.include_router(variables_router, prefix="/api")
app.include_router(groups_router, prefix="/api")
app.include_router(croissants_router, prefix="/api")

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

# Catch-all route for SPA (React Router)
@app.exception_handler(404)
async def custom_404_handler(request, __):
    if request.url.path.startswith("/api"):
        return JSONResponse(status_code=404, content={"detail": "Not Found"})

    # Re-evaluate static_dir in case it wasn't set globally or to be safe
    current_static_dir = None
    if os.path.exists(docker_static_dir):
        current_static_dir = docker_static_dir
    elif os.path.exists(local_static_dir):
        current_static_dir = local_static_dir
        
    if current_static_dir and os.path.exists(os.path.join(current_static_dir, "index.html")):
        return FileResponse(os.path.join(current_static_dir, "index.html"))
    return {"detail": "Not Found"}
