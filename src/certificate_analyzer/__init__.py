"""Certificate analyzer. Importing the package does not start the GUI."""


def main():
    from certificate_analyzer.cli import main as run

    return run()
