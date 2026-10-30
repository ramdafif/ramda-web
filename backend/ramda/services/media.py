import io
import re
import uuid
from pathlib import Path
from defusedxml import ElementTree as SafeET
from xml.etree import ElementTree as ET
from PIL import Image, UnidentifiedImageError
from flask import current_app
from ..models import db, MediaAsset

Image.MAX_IMAGE_PIXELS = 24_000_000
SVG_TAGS = {'svg', 'g', 'path', 'rect', 'circle', 'ellipse', 'polygon', 'polyline', 'line', 'title', 'desc', 'defs', 'linearGradient', 'radialGradient', 'stop', 'clipPath'}
SVG_ATTRS = {'viewBox', 'width', 'height', 'd', 'fill', 'stroke', 'stroke-width', 'stroke-linecap', 'stroke-linejoin', 'opacity', 'fill-opacity', 'stroke-opacity', 'transform', 'x', 'y', 'x1', 'x2', 'y1', 'y2', 'cx', 'cy', 'r', 'rx', 'ry', 'points', 'id', 'offset', 'stop-color', 'stop-opacity', 'gradientTransform', 'gradientUnits', 'clip-path', 'fill-rule'}


def sanitize_svg(raw):
    if b'<!DOCTYPE' in raw.upper() or b'<!ENTITY' in raw.upper():
        raise ValueError('SVG declarations are not allowed')
    try:
        root = SafeET.fromstring(raw)
    except Exception as exc:
        raise ValueError('Invalid SVG') from exc
    if root.tag.split('}')[-1] != 'svg':
        raise ValueError('Not an SVG')
    for parent in root.iter():
        for child in list(parent):
            if child.tag.split('}')[-1] not in SVG_TAGS:
                parent.remove(child)
        parent.tag = parent.tag.split('}')[-1]
        for key in list(parent.attrib):
            value = parent.attrib[key]
            if key not in SVG_ATTRS or re.search(r'(?:javascript:|data:|https?:|//|@import|expression)', value, re.I) or ('url(' in value and not re.fullmatch(r'url\(#[\w-]+\)', value)):
                del parent.attrib[key]
    root.set('xmlns', 'http://www.w3.org/2000/svg')
    try:
        viewbox = [float(v) for v in re.split(r'[ ,]+', root.attrib.get('viewBox', '').strip()) if v]
        width = int(float(root.attrib.get('width', '').removesuffix('px') or viewbox[2]))
        height = int(float(root.attrib.get('height', '').removesuffix('px') or viewbox[3]))
    except (ValueError, IndexError):
        raise ValueError('SVG needs numeric dimensions or a viewBox') from None
    if not 0 < width <= 10000 or not 0 < height <= 10000:
        raise ValueError('Invalid SVG dimensions')
    return ET.tostring(root, encoding='utf-8'), width, height


def store_media(file, alt):
    if not alt or len(alt) > 300:
        raise ValueError('Alt text is required (max 300 characters)')
    raw = file.read(8 * 1024 * 1024 + 1)
    if len(raw) > 8 * 1024 * 1024:
        raise ValueError('Maximum file size is 8 MB')
    uid = uuid.uuid4().hex
    output = Path(current_app.config['UPLOAD_DIR'])
    variants = []
    if (file.filename or '').lower().endswith('.svg'):
        encoded, width, height = sanitize_svg(raw)
        filename = f'{uid}.svg'
        (output / filename).write_bytes(encoded)
    else:
        try:
            with Image.open(io.BytesIO(raw)) as original:
                if original.format not in {'JPEG', 'PNG', 'WEBP', 'AVIF'} or original.width * original.height > 24_000_000:
                    raise ValueError('Only JPG, PNG, WebP and AVIF up to 24 MP are allowed')
                original.load()
                image = original.convert('RGBA' if 'A' in original.getbands() else 'RGB')
        except (UnidentifiedImageError, OSError, Image.DecompressionBombError) as exc:
            raise ValueError('Invalid image magic bytes or corrupt image') from exc
        width, height = image.size
        widths = sorted({min(width, n) for n in (320, 640, 960, 1440, 1920)})
        for size in widths:
            thumb = image.resize((size, max(1, round(height * size / width))), Image.Resampling.LANCZOS)
            for fmt in ('webp', 'avif'):
                name = f'{uid}-{size}.{fmt}'
                thumb.save(output / name, format=fmt.upper(), quality=78 if fmt == 'webp' else 65, exif=b'')
                variants.append({'src': f'/uploads/{name}', 'width': size, 'format': fmt})
        filename = f'{uid}-{widths[-1]}.webp'
        width = widths[-1]
        height = max(1, round(height * width / image.width))
    asset = MediaAsset(filename=filename, alt=alt, width=width, height=height, variants=variants)
    db.session.add(asset)
    db.session.flush()
    return asset
