"""Read Data — 制造测试工具入口。"""

from app.application import Application


if __name__ == "__main__":
    app = Application()
    app.create()
    app.show()
    app.run()
