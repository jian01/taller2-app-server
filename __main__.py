from create_application import create_application
import argparse


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Chotuve auth server')
    parser.add_argument('--config', help="The config file to use")
    args = parser.parse_args()
    if args.config:
        app = create_application(args.config)
    else:
        app = create_application()
    app.run()
