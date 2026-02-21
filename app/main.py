from fastapi import FastAPI
from app.api.routes import router
from app.settings import validate_data_pack, get_settings

app = FastAPI()
app.include_router(router)

_state = {}

@app.on_event("startup")
def startup():
    s = get_settings()
    versions = validate_data_pack()
    _state.update({"version_stamp": s.version_stamp, **versions})

@app.get("/health")
def health():
    return {"status": "ok", **_state}