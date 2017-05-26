import http.server
import json
import ssl

class BracketedHandler(http.server.BaseHTTPRequestHandler):
	def give_headers(self, code):
		self.send_response(code)
		self.send_header('Content-type', 'text/html')
		self.end_headers()

	def send_encoded(self, content):
		self.wfile.write(content.encode())

	def send_error(self, message):
		self.send_encoded(json.dumps({'error': True, 'errormsg': message}))

	def send_json(self, dict):
		self.send_encoded(json.dumps(dict))

	def do_HEAD(self):
		self.give_headers(501) # Not Implemented

	def do_GET(self):
		self.give_headers(200)
		pathparts = self.path.split('?', 1) # [0]: path, [1]: query string
		if pathparts[0] == '/':
			self.send_encoded('<!DOCTYPE html><html><head><title>[\] SERVER TEST</title></head><body>Server works, but click the link for a valid request <a href="/getprofile?1234">here</a></body></html>')
		elif pathparts[0] == '/getprofile':
			if len(pathparts) < 2:
				self.send_error('No ID was given to the server')
			else:
				# TODO: Get valid member from [\] (if error: self.send_error())
				self.send_json({
					'error': False,
					'snowflake': pathparts[1],
					'username': 'USERNAME',
					'discrim': '0000',
					'avatar': 'AVATAR (no webp please, firefox doesn\'t support that, and adding ?size=64 would be nice)',
					'status': 'online'
				})
		else:
			self.send_error('404: {}'.format(pathparts[0]))

httpd = http.server.HTTPServer(('', 4443), BracketedHandler)
httpd.socket = ssl.wrap_socket(
	httpd.socket,
	keyfile='C:\\Users\\David\\Documents\\cer\\somecert\\keyunenc.pem',
	certfile='C:\\Users\\David\\Documents\\cer\\somecert\\cert.pem',
	server_side=True
)
httpd.serve_forever()
