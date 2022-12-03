from os import getenv
from time import time
from typing import Any, TypeVar
from uuid import uuid1

from dotenv import load_dotenv
from eokulapi.eokulapi import EokulAPI
from eokulapi.Models.MarkLesson import MarkLesson
from feedgen.feed import FeedGenerator
from flask import Flask, redirect, render_template, url_for

load_dotenv()
emptylesson = MarkLesson(None, None, None, None, None, None, None, None, {}, {})


T = TypeVar("T")


def list_difference(l1: list[T], l2: list[T]) -> list[T]:
    return [x for x in l1 if x not in l2]


def dict_difference(d1: dict[T, Any], d2: dict[T, Any]) -> set[T]:
    return (set(d1) - set(d2)).union(set(d2) - set(d1))


CACHING_TIME: float = 60.0
"""cache timeout in seconds"""

last_update = 0.0

app = Flask(__name__)

user = EokulAPI(uid=getenv("EOKUL_UID", ""))
st = user.students[0]
user._update_marks(st)
state = st.marks.data if not getenv("APP_TEST_MSG") else []

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


def check_exam_result() -> list[tuple[str]]:
    global state
    global last_update
    global CACHING_TIME
    if (time() - last_update) < CACHING_TIME:
        return []
    last_update = time()
    user._update_marks(st)
    if state == st.marks.data:
        return []
    user._update_class_exam_average(st)
    newstate = st.marks.data
    diff = list_difference(newstate, state)
    result = []
    for changed_lesson in diff:
        old_changed_lessons = [l for l in state if changed_lesson.isMarkOfSelf(l)]
        old_changed_lesson = old_changed_lessons[0] if old_changed_lessons else emptylesson
        sozlu_diff = dict_difference(old_changed_lesson.sozlu, changed_lesson.sozlu)
        yazili_diff = dict_difference(old_changed_lesson.yazili, changed_lesson.yazili)
        for nth in yazili_diff:
            ort = [
                d.marks[nth].avg_mark
                for d in st.class_exam_average.data
                if changed_lesson.isAvgmarkOfSelf(d)
            ]
            result.append(
                (
                    f"{changed_lesson.mark_to_str(True,nth)} açıklanmış",
                    f"sınıf ortalaması: {ort[0] if ort else 'tuhaf bir şekilde belirsiz!?'}",
                )
            )
        for nth in sozlu_diff:
            result.append(
                (
                    f"{changed_lesson.mark_to_str(False,nth)} açıklanmış",
                    f"sınıf ortalaması: belirsiz",
                )
            )
    state = newstate
    return result
