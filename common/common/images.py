
import sys
from io import BytesIO

from PIL import Image

from common import database


def get_template(dbmanager, name, crop=None, location=None):
	"""Fetch the thumbnail template and any missing parameters from the database"""
	with dbmanager.get_conn() as conn:
		query = """
			SELECT image, crop, location FROM templates WHERE name = %s
		"""
		results = database.query(conn, query, name)
		row = results.fetchone()
		if row is None:
			raise ValueError('Template {} not found'.format(name))
		row = row._asdict()
		if not crop:
			crop = row['crop']
		if not location:
			location = row['location']

		return row['image'], crop, location


def compose_thumbnail_template(template_data, frame_data, crop, location):
	"""
	A thumbnail template consists of a byte stream representation of a PNG template image along with two 4-tuples [left x, top y, right x, bottom y] describing the crop and location of the frame. 

	To create a thumbnail, the input frame is first cropped to the bounds of the "crop" box, then resized to the size of the "location" box, then pasted underneath the template image at that
location within the template image.

	For example
	crop = (50, 100, 1870, 980)
	location = (320, 180, 1600, 900)
	would crop the input frame from (50, 100) to (1870, 980), resize it to 720x1280, and place it at (320, 180).
	"""

	# PIL can't load an image from a byte string directly, we have to pretend to be a file
	template = Image.open(BytesIO(template_data))
	frame = Image.open(BytesIO(frame_data))

	loc_left, loc_top, loc_right, loc_bottom = location
	location = loc_left, loc_top
	location_size = loc_right - loc_left, loc_bottom - loc_top

	# Create a new blank image of the same size as the template
	result = Image.new('RGBA', template.size)
	# Insert the frame at the desired location, cropping and scaling.
	# For choice of rescaling filter, pick LANCZOS (aka. ANTIALIAS) as it is highest quality
	# and we don't really care about performance.
	frame = frame.crop(crop).resize(location_size, Image.LANCZOS)
	result.paste(frame, location)
	# Place the template "on top", letting the frame be seen only where the template's alpha
	# lets it through.
	result.alpha_composite(template)

	buf = BytesIO()
	# PIL can't save an image to a byte string directly, we have to pretend to write it to
	# a file, rewind the file, then read it again.
	result.save(buf, format='png')
	buf.seek(0)
	return buf.read()


def cli(template, frame, crop, location):
	with open(template, "rb") as f:
		template = f.read()
	with open(frame, "rb") as f:
		frame = f.read()
	thumbnail = compose_thumbnail_template(template, frame, crop, location)
	sys.stdout.buffer.write(thumbnail)


if __name__ == '__main__':
	import argh
	argh.dispatch_command(cli)
