from http.server import SimpleHTTPRequestHandler, HTTPStatus, test
from textwrap import dedent

import argparse
import html
import io
import os
import re
import sys
import urllib

class RyukRequestHandler(SimpleHTTPRequestHandler):
    """Simple HTTP request handler with GET, HEAD and POST commands.

    This serves files from the current directory and any of its
    subdirectories.  The MIME type for files is determined by
    calling the .guess_type() method.

    The GET and HEAD requests are identical except that the HEAD
    request omits the actual contents of the file.

    The POST request allows for upload files.

    """
    def do_POST(self):
        success, info = self._post_data()
        result = "Success" if success else "Failed"
        self.log_message('{}: {} by: {}'.format(result, info, self.client_address))
        template_doc = dedent("""
        <!DOCTYPE HTML PUBLIC "-//W3C//DTD HTML 4.01//EN" "http://www.w3.org/TR/html4/strict.dtd">
        <html>
          <head>
            <meta http-equiv="Content-Type" content="text/html; charset={enc}">
            <title>Upload Result Page</title>
          </head>
          <body>
            <h2>Upload Result Page</h2>
            <hr>
            <strong>{result}:</strong>
            {info}
            <br>
            <a href="{back}">back</a>
          </body>
        </html>
        """)
        enc = sys.getfilesystemencoding()
        encoded = template_doc.format(
                enc=enc, back=self.headers['referer'],
                result=result, info=info
        ).encode(enc, 'surrogateescape')
        f = self._write_to_file(encoded)
        self._send_success_response(enc, encoded)
        if f:
            self.copyfile(f, self.wfile)
            f.close()

    def _send_success_response(self, enc, encoded):
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-type", "text/html; charset=%s" % enc)
        self.send_header("Content-Length", str(len(encoded)))
        self.end_headers()

    def _write_to_file(self, encoded):
        f = io.BytesIO()
        f.write(encoded)
        f.seek(0)
        return f

    def _get_filename(self, original_filename):
        """
        Return original_filename if it does not exist otherwise it creates a new
        file to avoid overriding the original one.
        """
        temp_filename = original_filename
        extension_position = original_filename.rfind('.')
        original_short_filename = original_filename[:extension_position]
        extension = original_filename[extension_position+1:]
        index = 1
        while os.path.exists(temp_filename):
            temp_filename = '{}-{}.{}'.format(
                    original_short_filename, index, extension)
            index += 1
        return temp_filename

    def _post_data(self):
        content_type = self.headers['content-type']
        if not content_type:
            return False, "Content-Type header doesn't contain boundary"
        boundary = content_type.split("=")[1].encode()
        remainbytes = int(self.headers['content-length'])
        line = self.rfile.readline()
        remainbytes -= len(line)
        if not boundary in line:
            return False, "Content NOT begin with boundary"
        line = self.rfile.readline()
        remainbytes -= len(line)
        fn = re.findall(r'Content-Disposition.*name="file"; filename="(.*)"', line.decode())
        if not fn:
            return False, "Can't find out file name..."
        path = self.translate_path(self.path)
        fn = os.path.join(path, fn[0])
        line = self.rfile.readline()
        remainbytes -= len(line)
        line = self.rfile.readline()
        remainbytes -= len(line)
        try:
            actual_filename = self._get_filename(fn)
            out = open(actual_filename, 'wb')
        except IOError:
            return False, "Can't create file to write, do you have permission to write?"

        preline = self.rfile.readline()
        remainbytes -= len(preline)
        while remainbytes > 0:
            line = self.rfile.readline()
            remainbytes -= len(line)
            if boundary in line:
                preline = preline[0:-1]
                if preline.endswith(b'\r'):
                    preline = preline[0:-1]
                out.write(preline)
                out.close()
                return True, "File '%s' upload success!" % actual_filename
            else:
                out.write(preline)
                preline = line
        return False, "Unexpect Ends of data."

    def list_directory(self, path):
        """Helper to produce a directory listing (absent index.html).

        Return value is either a file object, or None (indicating an
        error).  In either case, the headers are sent, making the
        interface the same as for send_head().
        """
        try:
            directory_content = os.listdir(path)
        except OSError:
            self.send_error(
                HTTPStatus.NOT_FOUND,
                "No permission to list directory")
            return None
        directory_content.sort(key=lambda a: a.lower())
        try:
            displaypath = urllib.parse.unquote(self.path,
                                               errors='surrogatepass')
        except UnicodeDecodeError:
            displaypath = urllib.parse.unquote(path)
        displaypath = html.escape(displaypath, quote=False)
        enc = sys.getfilesystemencoding()
        title = 'Directory listing for {}'.format(displaypath)
        template_doc = dedent("""
        <!DOCTYPE HTML PUBLIC "-//W3C//DTD HTML 4.01//EN" "http://www.w3.org/TR/html4/strict.dtd">
        <html>
          <head>
            <meta http-equiv="Content-Type" content="text/html; charset={enc}">
            <title>{title}</title>
          </head>
          <body>
            <h1>{title}</h1>
            <hr>
            <form ENCTYPE="multipart/form-data" method="post">
              <input name="file" type="file"/>
              <input type="submit" value="Upload"/>
            </form>
            <hr>
            <ul>
{list_files}
            </ul>
            <hr>
          </body>
        </html>
        """)
        list_files = ""
        template_list_files = """              <li><a href="{}">{}</a></li>\n"""
        # Back link anchor
        list_files += template_list_files.format("..", "..")

        for name in directory_content:
            fullname = os.path.join(path, name)
            displayname = linkname = name
            # Append / for directories or @ for symbolic links
            if os.path.isdir(fullname):
                displayname = name + "/"
                linkname = name + "/"
            if os.path.islink(fullname):
                displayname = name + "@"
                # Note: a link to a directory displays with @ and links with /

            list_files += template_list_files.format(
                    urllib.parse.quote(linkname, errors='surrogatepass'),
                    html.escape(displayname, quote=False)
            )
        encoded = template_doc.format(
                enc=enc, title=title, list_files=list_files
        ).encode(enc, 'surrogateescape')

        f = self._write_to_file(encoded)
        self._send_success_response(enc, encoded)
        return f


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--bind', '-b', default='', metavar='ADDRESS',
                        help='Specify alternate bind address '
                             '[default: all interfaces]')
    parser.add_argument('port', action='store',
                        default=8000, type=int,
                        nargs='?',
                        help='Specify alternate port [default: 8000]')
    args = parser.parse_args()
    handler_class = RyukRequestHandler
    test(HandlerClass=handler_class, port=args.port, bind=args.bind)
