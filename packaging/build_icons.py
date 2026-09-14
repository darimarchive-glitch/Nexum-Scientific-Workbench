"""Generate Windows icon sizes from the unchanged official SVG."""
from pathlib import Path
import io
import cairosvg
from PIL import Image
root=Path(__file__).resolve().parent.parent
svg=root/'docs/logo-nexum.svg'
if svg.read_bytes()!=(root/'nexum/assets/logo.svg').read_bytes():
    raise SystemExit('O logo do aplicativo precisa corresponder a docs/logo-nexum.svg.')
out=root/'build/icons';out.mkdir(parents=True,exist_ok=True)
png=cairosvg.svg2png(url=str(svg),output_width=256,output_height=256)
Image.open(io.BytesIO(png)).save(out/'nexum.ico',format='ICO',sizes=[(16,16),(24,24),(32,32),(48,48),(64,64),(128,128),(256,256)])
