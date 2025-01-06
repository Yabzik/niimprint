from fastapi import FastAPI, File, Form, UploadFile
from fastapi.responses import JSONResponse
from typing import Annotated, Optional

app = FastAPI()

from niimprint import BluetoothTransport, PrinterClient, SerialTransport
from niimprint.printer import InfoEnum

from PIL import Image
import io

@app.post("/print")
async def print_handler(
    density: Annotated[int, Form()],
    rotate: Annotated[int, Form()],
    image: Annotated[UploadFile, File()],
    labeltype: Optional[int] = Form(None)
):
    if density < 1 or density > app.state.max_density:
        return JSONResponse(
            status_code=400,
            content={"message": f"Density must be in range 1-{app.state.max_density}"}
        )
    if rotate not in [0, 90, 180, 270]:
        return JSONResponse(
            status_code=400,
            content={"message": "Rotate must be 0, 90, 180, or 270"}
        )
    if labeltype is None:
        labeltype = 1
    if labeltype < 1 or labeltype > 11:
        return JSONResponse(
            status_code=400,
            content={"message": "Label type must be in range 1-11"}
        )

    pil_image = Image.open(io.BytesIO(image.file.read()))
    if rotate != "0":
        # PIL library rotates counter clockwise, so we need to multiply by -1
        pil_image = pil_image.rotate(-int(rotate), expand=True)

    if pil_image.width > app.state.max_width_px:
        return JSONResponse(
            status_code=400,
            content={"message": f"Image width too big (max is {app.state.max_width_px})"}
        )

    printer = PrinterClient(app.state.transport)
    try:
        printer.print_image(pil_image, density=density)
        return {"density": density, "rotate": rotate, "image_size": image.size}
    except Exception:
        return JSONResponse(
            status_code=500,
            content={"message": "Failed to print"}
        )

@app.get('/info')
async def info_handler():
    printer = PrinterClient(app.state.transport)

    try:
        rfid_info = printer.get_rfid()
        state_info = printer.heartbeat()
        printer_info = {
            "serial": printer.get_info(InfoEnum.DEVICESERIAL),
            "soft_version": printer.get_info(InfoEnum.SOFTVERSION),
            "hard_version": printer.get_info(InfoEnum.HARDVERSION)
        }
        return {
            "stickers": rfid_info,
            "printer_info": printer_info,
            "state_info": state_info
        }
    except Exception:
        return JSONResponse(
            status_code=500,
            content={"message": "Failed to fetch info"}
        )


def send_heartbeat():
    printer = PrinterClient(app.state.transport)
    res = printer.heartbeat()
    print('Sent heartbeat', res)
