import logging
import re

import click
from PIL import Image

from niimprint import BluetoothTransport, PrinterClient, SerialTransport

import uvicorn
import niimprint.server
from apscheduler.schedulers.background import BackgroundScheduler

@click.group()
def cli():
    pass

@cli.command("print")
@click.option(
    "-m",
    "--model",
    type=click.Choice(["b1", "b18", "b21", "d11", "d110"], False),
    default="b21",
    show_default=True,
    help="Niimbot printer model",
)
@click.option(
    "-c",
    "--conn",
    type=click.Choice(["usb", "bluetooth"]),
    default="usb",
    show_default=True,
    help="Connection type",
)
@click.option(
    "-a",
    "--addr",
    help="Bluetooth MAC address OR serial device path",
)
@click.option(
    "-d",
    "--density",
    type=click.IntRange(1, 5),
    default=5,
    show_default=True,
    help="Print density",
)
@click.option(
    "-r",
    "--rotate",
    type=click.Choice(["0", "90", "180", "270"]),
    default="0",
    show_default=True,
    help="Image rotation (clockwise)",
)
@click.option(
    "-i",
    "--image",
    type=click.Path(exists=True),
    required=True,
    help="Image path",
)
@click.option(
    "-v",
    "--verbose",
    is_flag=True,
    help="Enable verbose logging",
)
def print_cmd(model, conn, addr, density, rotate, image, verbose):
    logging.basicConfig(
        level="DEBUG" if verbose else "INFO",
        format="%(levelname)s | %(module)s:%(funcName)s:%(lineno)d - %(message)s",
    )

    if conn == "bluetooth":
        assert conn is not None, "--addr argument required for bluetooth connection"
        addr = addr.upper()
        assert re.fullmatch(r"([0-9A-F]{2}:){5}([0-9A-F]{2})", addr), "Bad MAC address"
        transport = BluetoothTransport(addr)
    if conn == "usb":
        port = addr if addr is not None else "auto"
        transport = SerialTransport(port=port)

    if model in ("b1", "b18", "b21"):
        max_width_px = 384
    if model in ("d11", "d110"):
        max_width_px = 96

    if model in ("b18", "d11", "d110") and density > 3:
        logging.warning(f"{model.upper()} only supports density up to 3")
        density = 3

    image = Image.open(image)
    if rotate != "0":
        # PIL library rotates counter clockwise, so we need to multiply by -1
        image = image.rotate(-int(rotate), expand=True)
    assert image.width <= max_width_px, f"Image width too big for {model.upper()}"

    printer = PrinterClient(transport)
    printer.print_image(image, density=density)

@cli.command('server')
@click.option(
    "-m",
    "--model",
    type=click.Choice(["b1", "b18", "b21", "d11", "d110"], False),
    default="b21",
    show_default=True,
    help="Niimbot printer model",
)
@click.option(
    "-c",
    "--conn",
    type=click.Choice(["usb", "bluetooth"]),
    default="usb",
    show_default=True,
    help="Connection type",
)
@click.option(
    "-a",
    "--addr",
    help="Bluetooth MAC address OR serial device path",
)
@click.option(
    "-h",
    "--host",
    default="0.0.0.0",
    show_default=True,
    help="Web server host"
)
@click.option(
    "-p",
    "--port",
    "http_port_",
    type=click.IntRange(0, 65535),
    default="8080",
    show_default=True,
    help="Web server host"
)
@click.option(
    "-v",
    "--verbose",
    is_flag=True,
    help="Enable verbose logging",
)
def server_cmd(model, conn, addr, host, http_port_, verbose):
    logging.basicConfig(
        level="DEBUG" if verbose else "INFO",
        format="%(levelname)s | %(module)s:%(funcName)s:%(lineno)d - %(message)s",
    )
    
    if conn == "bluetooth":
        assert conn is not None, "--addr argument required for bluetooth connection"
        addr = addr.upper()
        assert re.fullmatch(r"([0-9A-F]{2}:){5}([0-9A-F]{2})", addr), "Bad MAC address"
        transport = BluetoothTransport(addr)
    if conn == "usb":
        port = addr if addr is not None else "auto"
        transport = SerialTransport(port=port)

    if model in ("b1", "b18", "b21"):
        max_width_px = 384
    if model in ("d11", "d110"):
        max_width_px = 96

    if model in ("b18", "d11", "d110"):
        max_density = 3
    else:
        max_density = 5
    
    scheduler = BackgroundScheduler()
    scheduler.add_job(niimprint.server.send_heartbeat, 'interval', seconds=60)
    scheduler.start()

    from niimprint.server import app

    app.state.transport = transport
    app.state.max_width_px = max_width_px
    app.state.max_density = max_density

    uvicorn.run("niimprint.server:app", host=host, port=http_port_, log_level="info")

if __name__ == "__main__":
    cli()
