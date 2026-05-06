import flet as ft

from src.app import AIHubApp


def main(page: ft.Page) -> None:
    AIHubApp(page).build()


if __name__ == "__main__":
    runner = getattr(ft, "run", None) or ft.app
    runner(main)
