# ezcomic

ezcomic is a blog style script for hosting comic book websites, written using Flask for Python 3.

After installation, register an administrator account to post, edit and reorder comics.

## Installation

A working installation of Python 3 is required. 

Clone the repository using git, or download and extract a zip file of the latest release.

### Windows
* Install [python3](https://www.python.org/downloads)
* Install [pip3](https://pip.pypa.io/en/stable/installing)
* Open a command prompt
* `pip3 install virtualenv`
* `C:\python34\Scripts\virtualenv venv`
* `venv\Scripts\activate.bat`
* `C:\python34\Scripts\pip3 install -r requirements.txt`
* `copy config.py-dist config.py`
Edit `config.py` to specify a title and secret.

### Linux
* Install python3, pip3, virtualenv
* `virtualenv venv`
* `source ./venv/scripts/activate`
* `pip3 install -r requirements.txt`
* `cp config.py-dist config.py`
Edit `config.py` to specify a title and secret.

## Usage
`python ezcomic.py`
Open http://localhost:5000 in your browser.

## uwsgi
Edit the included uwsgi.json config file appropriately, and run with `uwsgi uwsgi.json`.
Configure your web server to proxy requests to the appropriate port.

## Reuse
This codebase may be useful for reference to Flask beginners. It is a simple 2 page application which includes the following:

* Flask with Jinja2 templating
* Data storage using SQLAlchemy ORM with sqlite, easily adaptable to MySQL
* Correct usage of bcrypt with individual salts
* User accounts with registration and permissions using flask_login

## License

Released under [GNU GPLv3](http://www.gnu.org/licenses/gpl-3.0.en.html)