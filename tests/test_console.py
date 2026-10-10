from app.scripts.console import main


def test_main(settings):
    main(settings, start_shell=lambda **kwargs: None)
