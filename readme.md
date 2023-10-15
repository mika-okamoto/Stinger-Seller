## Stinger Seller

Educational (?) project.

## How do I develop this?

On MacOS/Linux:

```sh
python -m venv venv/
. venv/bin/activate
pip install -r requirements.txt
python -m spacy download en_core_web_sm
```

On Windows:
```sh
python -m venv venv/
./venv/Scripts/activate
pip install -r requirements.txt
python -m spacy download en_core_web_sm
```

## How do I run this?

Now, just:
```sh
flask --app app init-db
flask --app app run --debug
```

If you want some demonstration data, run:
```sh
flask --app app seed-db
```
