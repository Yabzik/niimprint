from fastapi import FastAPI, File, Form, UploadFile
from fastapi.responses import JSONResponse
from typing import Annotated

app = FastAPI()

from niimprint import BluetoothTransport, PrinterClient, SerialTransport
from niimprint.printer import InfoEnum

from PIL import Image
import io

@app.post("/print")
async def print_handler(
    density: Annotated[int, Form()],
    rotate: Annotated[int, Form()],
    image: Annotated[UploadFile, File()]
):
    if density < 1 or density > 5:
        return JSONResponse(status_code=400, content={"message": "Density must be in range 1-5"})
    if rotate not in [0, 90, 180, 270]:
        return JSONResponse(status_code=400, content={"message": "Rotate must be 0, 90, 180, or 270"})

    pil_image = Image.open(io.BytesIO(image.file.read()))
    if rotate != "0":
        # PIL library rotates counter clockwise, so we need to multiply by -1
        pil_image = pil_image.rotate(-int(rotate), expand=True)
    assert pil_image.width <= 384, "Image width too big"

    transport = SerialTransport(port="/dev/ttyACM0")
    printer = PrinterClient(transport)
    printer.print_image(pil_image, density=density)

    return {"density": density, "rotate": rotate, "image_size": image.size}


@app.get('/info')
async def info_handler():
    transport = SerialTransport(port="/dev/ttyACM0")
    printer = PrinterClient(transport)

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


def send_heartbeat():
    transport = SerialTransport(port="/dev/ttyACM0")
    printer = PrinterClient(transport)
    res = printer.heartbeat()
    print('Sent heartbeat', res)
