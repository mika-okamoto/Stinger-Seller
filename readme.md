# Stinger Seller

Educational project for Hack GT X

College students in our generation often come with unlimited wants and short-attention spans. As a result, on many social media platforms we often see students attempting to sell their used items or trying to buy new items for cheap, but failing to execute any transaction either due to a fear of their payment security or unable to find their desired item. And thus, Stinger Seller was born! We wanted to create a secure marketplace for all Georgia Tech students to not only live sustainably, but also promote increased accessibility of educational materials, especially given the rising costs of academic resources.

We unite and foster efficiency for constantly-busy college students, specifically Georgia Tech students, on a consolidated platform solely for buying and selling items. We're a one stop shop for all your wants and needs.

We have a monolithic Flask application that uses an SQLite database to keep track of all listed items and all sellers. We use Stripe Connect to route payments between buyers and sellers in a secure manner. We have a search feature that implements sentiment searching using natural language processing methods alongside filtering and simple querying. We utilized Spacy to tokenize word data, doc2bow to vectorize each token, and gensim as our model to match similarities. We used tagging in parallel to our search feature, to allow the users to easily filter by specific categories in addition to their desired searches.

## Demo: 

### Demo Video
[![Demo Video](https://img.youtube.com/vi/YYy7w4GJuvk/0.jpg)](https://www.youtube.com/watch?v=YYy7w4GJuvk)

### [Devpost](https://devpost.com/software/stinger-seller)

### Homepage
![homepage](https://github.com/mika-okamoto/Stinger-Seller/assets/40896683/cfd6db53-7ec4-4be7-a9e1-e11b4c3f2398)

### Searching for "pencil"
![searching](https://github.com/mika-okamoto/Stinger-Seller/assets/40896683/c3c729d5-acc6-44d8-9b24-9b725a7797dc)

### Profile Page
![profile](https://github.com/mika-okamoto/Stinger-Seller/assets/40896683/74b9be45-c9c0-4260-9498-c4c55716f34c)

### Adding item to sell
![adding item](https://github.com/mika-okamoto/Stinger-Seller/assets/40896683/3e4a5378-213e-4b31-9763-068a7f5bfa0c)


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
