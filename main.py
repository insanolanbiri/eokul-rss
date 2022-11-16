from os import getenv
from time import time
from uuid import uuid1

from dotenv import load_dotenv
from eokulapi.eokulapi import EokulAPI
from eokulapi.Models.MarkLesson import MarkLesson
from feedgen.feed import FeedGenerator
from flask import Flask, redirect, url_for, render_template

load_dotenv()
emptylesson = MarkLesson(None, None, None, None, None, None, None, None, {}, {})

list_difference = lambda l1, l2: [x for x in l1 if x not in l2]


def dict_difference(d1: dict, d2: dict) -> set:
    return (set(d1) - set(d2)).union(set(d2) - set(d1))


hostname = getenv("APP_HOSTNAME", "http://localhost:5000")
fg = FeedGenerator()
fg.title("sınav sonuçları")
fg.link(href="/feeds/sinav_sonuc_atom.xml", rel="self")
fg.author({"name": "insanolanbiri", "email": "insanolanbiri@insanolanbiri.org"})
fg.id(f"{hostname}/feeds/sinav_sonuc_atom.xml")
fg.icon(f"{hostname}/static/little_logo.png")
fg.image(f"{hostname}/static/little_logo.png")
fg.logo(f"{hostname}/static/little_logo.png")
fg.subtitle("bir okulun bir sınıfının sınavlarının açıklanıp açıklanmadığı ve sınıf ortalaması")
fg.language("tr")

app = Flask(__name__)


user = EokulAPI(uid=getenv("EOKUL_UID", ""))
st = user.students[0]
user._update_marks(st)
state = st.marks.data
last_update = 0.0


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/favicon.ico")
def favicon():
    return redirect(url_for("static", filename="the_logo.png"))


@app.route("/feeds/sinav_sonuc_atom.xml", methods=["GET"])
def send_exam_result_atom():
    mesg = check_exam_result()
    if mesg:
        for i in mesg:
            fe = fg.add_entry()
            fe.title(i[0])
            fe.description(i[1])
            fe.id(uuid1().hex)
    return fg.atom_str()


@app.route("/feeds/sinav_sonuc_rss.xml", methods=["GET"])
def send_exam_result_rss():
    mesg = check_exam_result()
    if mesg:
        for i in mesg:
            fe = fg.add_entry()
            fe.title(i[0])
            fe.description(i[1])
            fe.id(uuid1().hex)
    return fg.rss_str()


def check_exam_result() -> list[tuple[str]]:
    global state
    global last_update
    if not time() - last_update > 60:
        return []
    last_update = time()
    user._update_marks(st)
    if state == st.marks.data:
        return []
    user._update_class_exam_average(st)
    newstate = st.marks.data
    diff = list_difference(newstate, state)
    result = []
    for i in diff:
        changed_lesson: MarkLesson = i
        old_changed_lessons = [
            lesson for lesson in state if lesson.lesson_id == changed_lesson.lesson_id
        ]
        old_changed_lesson: MarkLesson = (
            old_changed_lessons[0] if old_changed_lessons else emptylesson
        )
        ders = changed_lesson.lesson
        sozlu_diff = dict_difference(old_changed_lesson.sozlu, changed_lesson.sozlu)
        yazili_diff = dict_difference(old_changed_lesson.yazili, changed_lesson.yazili)
        for nth in yazili_diff:
            dtype = "yazılı"
            for d in st.class_exam_average.data:
                if d.lesson_name == ders:
                    ort = d.marks[nth].avg_mark
                    break
            result.append(
                (
                    f"{ders.replace('I','ı').lower()} {nth}. {dtype} açıklanmış",
                    f"sınıf ortalaması: {ort}",
                )
            )
        for nth in sozlu_diff:
            dtype = "sözlü"
            ort = "belirsiz"
            result.append(
                (
                    f"{ders.replace('I','ı').lower()} {nth}. {dtype} açıklanmış",
                    f"sınıf ortalaması: {ort}",
                )
            )
    state = newstate
    return result
