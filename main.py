"""serial-test-automation"""

from app.application import Application


if __name__ == "__main__":
    app = Application()
    app.create()
    app.show()
    app.run()
