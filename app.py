import os

from flask import Flask, render_template, redirect, url_for
from flask_bootstrap import Bootstrap
from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField
from wtforms.validators import DataRequired
import requests

app = Flask(__name__)
app.config['SECRET_KEY'] = 'C2HWGVoMGfNTBsrYQg8EfAb'
Bootstrap(app)


def ask_ao3_external_api(first_tag, second_tag):
    ao3_data = requests.get("https://fandomstats.org/api/v1.0/stats?tag_id=" + first_tag + "&other_tag_names[]=" + second_tag)
    data = ao3_data.json()
    return data


def ask_moviedb_external_api(fandom):
    headers = {
        'x-rapidapi-host': "online-movie-database.p.rapidapi.com",
        'x-rapidapi-key': "2f53c04e38msh7d8017281ad03a0p1c00d0jsn00a7f9711a23"
    }

    id_url = "https://online-movie-database.p.rapidapi.com/title/find"
    id_query = {"q": fandom}
    id_response = requests.request("GET", id_url, headers=headers, params=id_query)

    fandom_id = id_response.json()['results'][0]['id']
    fandom_id_clean = fandom_id.split('/')[2]

    plot_url = "https://online-movie-database.p.rapidapi.com/title/get-plots"
    plot_query = {"tconst": fandom_id_clean}
    plot_response = requests.request("GET", plot_url, headers=headers, params=plot_query)

    plot = plot_response.json()['plots'][0]['text']

    return plot


def ask_image_external_api(first_tag, second_tag):
    url = "https://bing-image-search1.p.rapidapi.com/images/search"
    headers = {
        'x-rapidapi-host': "bing-image-search1.p.rapidapi.com",
        'x-rapidapi-key': "2f53c04e38msh7d8017281ad03a0p1c00d0jsn00a7f9711a23"
    }
    first_query = {"q": first_tag}
    second_query = {"q": second_tag}

    first_response = requests.request("GET", url, headers=headers, params=first_query)
    second_response = requests.request("GET", url, headers=headers, params=second_query)

    first_photo_url = first_response.json()['value'][0]['thumbnailUrl']
    second_photo_url = second_response.json()['value'][0]['thumbnailUrl']

    return first_photo_url, second_photo_url


def do_some_logic(first_tag, second_tag):
    # get ao3 stats
    data_ao3 = ask_ao3_external_api(first_tag, second_tag)
    # do some more here !!!

    # get plot for the fandom
    fandom = list(data_ao3['stats']['fandom'].keys())[0].split('-')[0]
    fandom_plot = ask_moviedb_external_api(fandom)

    # get photo for each tag
    first_photo_url, second_photo_url = ask_image_external_api(first_tag, second_tag)

    return first_tag, second_tag, first_photo_url, second_photo_url, fandom, fandom_plot


class NameForm(FlaskForm):
    first_tag = StringField('Enter the first tag:', validators=[DataRequired()])
    second_tag = StringField('Enter the second tag:', validators=[DataRequired()])
    submit = SubmitField('Submit')


@app.route('/', methods=['GET', 'POST'])
def index():
    form = NameForm()
    if form.is_submitted():
        first_tag = form.first_tag.data
        second_tag = form.second_tag.data
        return redirect(url_for('results', first_tag=first_tag, second_tag=second_tag))
    return render_template('index.html', form=form)


@app.route('/results/<first_tag>/<second_tag>')
def results(first_tag, second_tag):
    first_tag, second_tag, first_photo_url, second_photo_url, fandom, fandom_plot = \
        do_some_logic(first_tag, second_tag)

    return render_template('results.html', first_tag=first_tag, second_tag=second_tag, first_photo=first_photo_url,
                           second_photo=second_photo_url, fandom=fandom, fandom_plot=fandom_plot)


@app.errorhandler(404)
def page_not_found(e):
    return render_template('404.html'), 404


@app.errorhandler(500)
def internal_server_error(e):
    return render_template('500.html'), 500


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
