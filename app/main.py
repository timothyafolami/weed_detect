from fastapi import FastAPI, WebSocket, WebSocketDisconnect, UploadFile, File, Request
from fastapi.responses import JSONResponse, HTMLResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from detection import initialize_directories, slice_geotiff, detect_weeds_in_slices, cleanup, create_zip  # Import detection functions
from db_user_info import insert_user_info
from db_bucket import upload_file_to_bucket
from typing import List
from io import BytesIO

app = FastAPI()

# Mount static files
app.mount("/static", StaticFiles(directory="static"), name="static")

# WebSocket manager
class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)

    async def send_message(self, message: str):
        for connection in self.active_connections:
            await connection.send_text(message)

manager = ConnectionManager()

@app.get("/", response_class=HTMLResponse)
async def read_index():
    with open("static/index.html") as f:
        return HTMLResponse(content=f.read())

@app.get("/app", response_class=HTMLResponse)
async def read_app():
    with open("static/app.html") as f:
        return HTMLResponse(content=f.read())

@app.post("/register")
async def register_user(request: Request):
    user_info = await request.json()
    try:
        insert_user_info(user_info)
        return JSONResponse(content={"detail": "User registered successfully"}, status_code=200)
    except Exception as e:
        return JSONResponse(content={"detail": str(e)}, status_code=400)

@app.post("/upload_geotiff/")
async def upload_geotiff(file: UploadFile = File(...)):
    # Initialize directories at the start
    initialize_directories()

    file_location = f"uploaded_geotiff.tif"
    with open(file_location, "wb") as f:
        f.write(file.file.read())

    await manager.send_message("GeoTIFF file uploaded successfully. Slicing started.")
    slices = await slice_geotiff(file_location, slice_size=3000)
    await manager.send_message("Slicing complete. Starting weed detection.")
    weed_bboxes = await detect_weeds_in_slices(slices)
    await manager.send_message("Weed detection complete. Generating shapefile.")

    # Create zip file
    zip_file_path = await create_zip()
    await manager.send_message("Shapefiles Generated. Zipping shapefile.")
    
    # Upload the zip file to the bucket
    response = upload_file_to_bucket(zip_file_path)
    print(response)
    await manager.send_message("Zip file uploaded to bucket storage.")

    # Read zip file into buffer for download
    zip_buffer = BytesIO()
    with open(zip_file_path, 'rb') as f:
        zip_buffer.write(f.read())
    zip_buffer.seek(0)

    # Cleanup files and directories
    cleanup()

    return StreamingResponse(zip_buffer, media_type="application/zip", headers={"Content-Disposition": "attachment; filename=weed_detections.zip"})

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            data = await websocket.receive_text()
            await manager.send_message(data)
    except WebSocketDisconnect:
        manager.disconnect(websocket)
