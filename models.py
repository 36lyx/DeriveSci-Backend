"""DeriveSci-Backend/models.py
Copyright (c) 2026 Louis Liu  All rights reserved.

数据库模型模块，实现网站所需的数据库操作。
"""

import io
import csv
import json
import datetime
import functools
import mimetypes

from flask import url_for
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from werkzeug.security import generate_password_hash, check_password_hash
from sqlalchemy import MetaData
from sqlalchemy.dialects.mysql import MEDIUMBLOB

from anschecker import check_answers, testpoints_passedlist

__all__ = [
    "init_app",
    "db",
    "csv2list",
    "list2csv",
    "utcfromnow",
    "get_post",
    "find_user",
    "register_user",
    "unregister_user",
    "Prob",
    "Tag",
    "get_prob",
    "add_prob",
    "get_solution",
    "add_solution",
    "add2tags",
    "Submission",
    "Image",
    "add_images",
    "get_images_for_post",
    "get_image",
    "Article",
    "get_article",
    "add_article",
    "Comment",
    "get_comment",
    "clear_comments",
    "update_chatlastvisit",
]

convention = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}
metadata = MetaData(naming_convention=convention)
db = SQLAlchemy(metadata=metadata)
migrate = Migrate(db=db, compare_type=True)


def init_app(app):
    db.init_app(app)
    migrate.init_app(app)


def csv2list(csvstr):
    return next(csv.reader((csvstr,), skipinitialspace=True))


def list2csv(ls):
    csvstr = io.StringIO()
    writer = csv.writer(csvstr)
    writer.writerow(list(ls))
    return csvstr.getvalue().splitlines()[0]


_utcnow = functools.partial(datetime.datetime.now, datetime.UTC)


def utcfromnow(timestamp):
    return _utcnow() - timestamp.astimezone(datetime.UTC)


def datetime2iso(timestamp: datetime.datetime):
    if timestamp.tzinfo is None:
        timestamp = timestamp.replace(tzinfo=datetime.UTC)
    else:
        timestamp = timestamp.astimezone(datetime.UTC)
    return timestamp.isoformat(timespec="seconds").replace("+00:00", "Z")


# =========================== 用户数据库与登录系统 ===========================


class User(db.Model):
    __tablename__ = "users"
    columns = "uid", "name", "password"
    uid = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(64), unique=True, nullable=False)
    gender = db.Column(db.Integer, default=0, server_default="0")
    password = db.Column(db.String(256), nullable=False)
    introduction = db.Column(db.Text)
    avatar = db.Column(MEDIUMBLOB())
    avmimetype = db.Column(db.String(64))
    avlastmodified = db.Column(
        db.DateTime,
        default=db.func.utc_timestamp(),
        server_default=db.func.utc_timestamp(),
        onupdate=db.func.utc_timestamp(),
        server_onupdate=db.func.utc_timestamp(),
    )
    submissions = db.relationship("Submission", backref="user", cascade="all, delete")
    uploadedprobs = db.relationship("Prob", backref="source")
    solutions = db.relationship("ProbSolution", backref="user")
    articles = db.relationship("Article", backref="user")
    comments = db.relationship("Comment", backref="user")
    cmtlastvisit = db.Column(
        db.DateTime,
        default=db.func.utc_timestamp(),
        server_default=db.func.utc_timestamp(),
    )
    isadmin = db.Column(db.Boolean, default=False, server_default="0")

    def verify_password(self, password):
        return (
            False
            if self.password is None
            else check_password_hash(self.password, password)
        )

    def edit_profile(self, name, password, password_confirmation, avatarfile, gender):
        user_exists = db.session.query(
            User.query.filter_by(name=name).exists()
        ).scalar()
        if name != self.name and user_exists:
            return "User name has been used."
        elif password != password_confirmation:
            return "Password confirmation failed."
        elif not name:
            return "Empty user name."
        avatardata = avatarfile.read()
        if name and name != self.name:
            self.name = name
        if password and not self.verify_password(password):
            self.password = generate_password_hash(password)
        if avatardata:
            self.avatar = avatardata
            self.avmimetype = mimetypes.guess_type(avatarfile.filename)[0]
            self.avlastmodified = _utcnow()
        if gender != self.gender:
            self.gender = gender
        db.session.commit()

    def get_probscores(self):
        probscores = {}
        for submission in self.submissions:
            prob = submission.prob
            if (
                prob not in probscores
                or prob in probscores
                and probscores[prob] < submission.score
            ):
                probscores[prob] = submission.score
        return probscores

    def get_passedprobs(self):
        return sorted(
            [prob for prob, score in self.get_probscores().items() if score == 100]
        )

    def unread_reply_comments(self):
        is_mine = Comment.replyto.has(Comment.uid == self.uid)
        return (
            Comment.query.filter(
                is_mine
                if self.cmtlastvisit is None
                else is_mine & (self.cmtlastvisit < Comment.timestamp)
            )
            .order_by(Comment.timestamp.desc())
            .all()
        )

    def unread_comments_on_my_probs(self):
        probnos = [prob.probno for prob in self.uploadedprobs]
        if not probnos:
            return []
        query = Comment.query.filter(
            Comment.post_type == 0,
            Comment.post_ident.in_(probnos),
            Comment.replyto_id.is_(None),
        )
        if self.cmtlastvisit is not None:
            query = query.filter(Comment.timestamp > self.cmtlastvisit)
        return query.order_by(Comment.timestamp.desc()).all()

    def unread_comments_on_my_solutions(self):
        sol_ids = [solution.get_post_ident() for solution in self.solutions]
        if not sol_ids:
            return []
        query = Comment.query.filter(
            Comment.post_type == 1,
            Comment.post_ident.in_(sol_ids),
            Comment.replyto_id.is_(None),
        )
        if self.cmtlastvisit is not None:
            query = query.filter(Comment.timestamp > self.cmtlastvisit)
        return query.order_by(Comment.timestamp.desc()).all()

    def unread_comments_count(self):
        reply_query = Comment.query.filter(Comment.replyto.has(Comment.uid == self.uid))
        probnos = [prob.probno for prob in self.uploadedprobs]
        solution_ids = [solution.get_post_ident() for solution in self.solutions]
        prob_query = (
            Comment.query.filter(
                Comment.post_type == 0,
                Comment.post_ident.in_(probnos),
                Comment.replyto_id.is_(None),
            )
            if probnos
            else None
        )
        sol_query = (
            Comment.query.filter(
                Comment.post_type == 1,
                Comment.post_ident.in_(solution_ids),
                Comment.replyto_id.is_(None),
            )
            if solution_ids
            else None
        )
        if self.cmtlastvisit is not None:
            reply_query = reply_query.filter(Comment.timestamp > self.cmtlastvisit)
            if prob_query is not None:
                prob_query = prob_query.filter(Comment.timestamp > self.cmtlastvisit)
            if sol_query is not None:
                sol_query = sol_query.filter(Comment.timestamp > self.cmtlastvisit)
        total = reply_query.count()
        if prob_query is not None:
            total += prob_query.count()
        if sol_query is not None:
            total += sol_query.count()
        return total

    def unread_comment_sections(self):
        return {
            "replies": self.unread_reply_comments(),
            "prob_comments": self.unread_comments_on_my_probs(),
            "solution_comments": self.unread_comments_on_my_solutions(),
        }

    def update_cmtlastvisit(self):
        self.cmtlastvisit = _utcnow()
        db.session.commit()

    def chat_to(self, uid, msg):
        message = Comment(user=self, content=str(msg), post_type=2, post_ident=str(uid))
        db.session.add(message)
        db.session.commit()

    def all_chats(self, from_time=None):
        if from_time is None:
            from_time = datetime.datetime.min
        chats_list = (
            Comment.query.filter(
                Comment.post_type == 2,
                Comment.timestamp > from_time,
                (Comment.uid == self.uid) | (Comment.post_ident == str(self.uid)),
            )
            .order_by(Comment.timestamp.asc())
            .all()
        )
        chats, lastvisits = {}, {}
        for chatmsg in chats_list:
            other, othersend = chatmsg.uid, True
            if other == self.uid:
                other, othersend = int(chatmsg.post_ident), False
            if other not in chats:
                chats[other] = {"unread": 0, "messages": []}
            chats[other]["messages"].append(
                {
                    "content": chatmsg.content,
                    "othersend": othersend,
                    "timestamp": chatmsg.timestamp.isoformat(),
                }
            )
            if other not in lastvisits:
                lastvisits[other] = max(
                    get_chatlastvisit(self.uid, other).lastvisit, from_time
                )
            chats[other]["unread"] += (
                othersend and lastvisits[other] < chatmsg.timestamp
            )
        return chats

    def unread_chats_num(self):
        chats_list = (
            Comment.query.filter(
                Comment.post_type == 2, Comment.post_ident == str(self.uid)
            )
            .order_by(Comment.timestamp.asc())
            .all()
        )
        unread_num, lastvisits = 0, {}
        for chatmsg in chats_list:
            other = chatmsg.uid
            if other not in lastvisits:
                lastvisits[other] = get_chatlastvisit(self.uid, other).lastvisit
            unread_num += lastvisits[other] < chatmsg.timestamp
        return unread_num

    def avatar_url(self, anchor=None, **kwargs):
        return (
            url_for("auth.avatar", uid=self.uid, _anchor=anchor, **kwargs)
            if self.avatar
            else "/favicon-inverted.svg"
        )

    def to_dict(self):
        return {
            "uid": self.uid,
            "userName": self.name,
            "isAdmin": self.isadmin,
            "gender": self.gender,
            "introduction": self.introduction,
            "avatar": self.avatar_url(),
        }


def find_user(val, key="uid"):
    if not val or key not in User.columns:
        return None
    user = (
        db.session.get(User, val)
        if key == "uid"
        else User.query.filter_by(**{key: val}).first()
    )
    return user


def register_user(name, gender, password, avatarfile):
    user_exists = db.session.query(User.query.filter_by(name=name).exists()).scalar()
    if name and password and not user_exists:
        user = User(name=name, gender=gender, password=generate_password_hash(password))
        if avatarfile is not None:
            user.avatar = avatarfile.read()
            user.avmimetype = mimetypes.guess_type(avatarfile.filename)[0]
        db.session.add(user)
        db.session.commit()
        return True, user
    elif user_exists:
        return False, "User name has been used."
    else:
        return False, "Fail to register."


def unregister_user(user):
    if user is not None:
        db.session.delete(user)
        db.session.commit()


# =========================== 图片数据库 ===========================


class Image(db.Model):
    __tablename__ = "images"
    post_type = db.Column(db.Integer, primary_key=True)
    post_ident = db.Column(db.String(64), primary_key=True)
    name = db.Column(db.String(64), primary_key=True)
    uid = db.Column(db.Integer, db.ForeignKey("users.uid", ondelete="set null"))
    size = db.Column(db.Integer)
    mimetype = db.Column(db.String(64))
    data = db.Column(MEDIUMBLOB())
    timestamp = db.Column(
        db.DateTime,
        default=db.func.utc_timestamp(),
        server_default=db.func.utc_timestamp(),
    )
    uploader = db.relationship("User", backref="uploaded_images")


def add_images(user, post_type, post_ident, imgfiles):
    for imgfile in imgfiles:
        if get_image(post_type, post_ident, imgfile.filename) is not None:
            return "File name has been used."
    for imgfile in imgfiles:
        imgdata = imgfile.read()
        if len(imgdata):
            img = Image(
                post_type=int(post_type),
                post_ident=str(post_ident),
                name=imgfile.filename,
                uid=user.uid,
                size=len(imgdata),
                data=imgdata,
                mimetype=mimetypes.guess_type(imgfile.filename)[0],
            )
            db.session.add(img)
    db.session.commit()


def get_images_for_post(post_type, post_ident):
    return (
        Image.query.filter_by(post_type=int(post_type), post_ident=str(post_ident))
        .order_by(Image.name.asc())
        .all()
    )


def get_image(post_type, post_ident, name):
    return db.session.get(Image, (int(post_type), str(post_ident), str(name)))


# =========================== 题目数据库 ===========================


prob_tag = db.Table(
    "probs_tags",
    db.Column(
        "probno",
        db.String(16),
        db.ForeignKey("probs.probno", ondelete="cascade", onupdate="cascade"),
        primary_key=True,
    ),
    db.Column(
        "tagtitle",
        db.String(16),
        db.ForeignKey("tags.tagtitle", ondelete="cascade", onupdate="cascade"),
        primary_key=True,
    ),
)


class Prob(db.Model):
    __tablename__ = "probs"
    probno = db.Column(db.String(16), primary_key=True)
    probtitle = db.Column(db.String(64))
    timestamp = db.Column(
        db.DateTime,
        default=db.func.utc_timestamp(),
        server_default=db.func.utc_timestamp(),
    )
    tags = db.relationship(
        "Tag", secondary=prob_tag, back_populates="probs", collection_class=set
    )
    statement = db.Column(db.Text, nullable=False)
    answer = db.Column(db.Text)
    solutions = db.relationship("ProbSolution", backref="prob", cascade="all, delete")
    sourceuid = db.Column(db.Integer, db.ForeignKey("users.uid", ondelete="set null"))
    submissions = db.relationship("Submission", backref="prob", cascade="all, delete")
    review_status = db.Column(db.Integer, default=-1, server_default="-1")
    isofficial = db.Column(db.Boolean, default=False, server_default="0")
    review_comment = db.Column(db.Text)
    post_type = 0

    def get_answer(self):
        if not self.answer:
            return []
        answer = json.loads(self.answer)
        if not isinstance(answer, list):
            return []
        return answer

    def check_answers(self, userans):
        answers = self.get_answer()
        if not answers:
            return None, []
        if isinstance(userans, str):
            userans_list = [userans]
        elif isinstance(userans, list):
            userans_list = userans
        else:
            userans_list = [str(userans)]

        answer_evals = []
        testpoints_list = []
        for i, sub in enumerate(answers):
            ua = userans_list[i] if i < len(userans_list) else ""
            tps_def = sub["tps"]
            ua_eval, tps = check_answers(tps_def, ua)
            answer_evals.append(ua_eval)
            testpoints_list.append(tps)
        return answer_evals, testpoints_list

    def add_submission(self, user, answer):
        answer_eval, testpoints = self.check_answers(answer)
        passedlist = []
        for sub in testpoints:
            passedlist.extend(testpoints_passedlist(sub))
        stored_answer = json.dumps(answer) if not isinstance(answer, str) else answer
        submission = Submission(
            user=user,
            answer=stored_answer,
            ispassed=all(passedlist) if passedlist else False,
            score=100 * sum(passedlist) // len(passedlist) if passedlist else 0,
        )
        db.session.add(submission)
        submission.prob = self
        db.session.commit()
        return answer_eval, testpoints, submission

    def get_toplevel_comments(self):
        return (
            Comment.query.filter(
                Comment.post_type == 0,
                Comment.post_ident == self.probno,
                Comment.replyto_id.is_(None),
            )
            .order_by(Comment.timestamp.desc())
            .all()
        )

    def edit(self, probtitle, tags, statement, answer):
        if probtitle:
            self.probtitle = probtitle
        if statement:
            self.statement = statement
        self.answer = answer
        self.tags = {get_tag(tagtitle, create=True) for tagtitle in tags}
        db.session.commit()

    def viewable_for(self, user: User | None):
        return (
            self.review_status == 1
            or user is not None
            and (user == self.source or user.isadmin)
        )

    def editable_for(self, user: User | None):
        return user is not None and (user == self.source or user.isadmin)

    def get_post_ident(self):
        return self.probno

    def to_dict(self):
        return {
            "probNo": self.probno,
            "title": self.probtitle,
            "lastModifiedAt": datetime2iso(self.timestamp),
            "tags": [tag.tagtitle for tag in self.tags],
            "statement": self.statement,
            "isOfficial": self.isofficial,
            "reviewStatus": self.review_status,
            "reviewComment": self.review_comment,
        }

    def __str__(self):
        return f"问题 {self.probno}"

    def __lt__(self, prob):
        return self.probno < prob.probno


class Submission(db.Model):
    __tablename__ = "submissions"
    submitid = db.Column(db.Integer, primary_key=True)
    probno = db.Column(
        db.String(16), db.ForeignKey("probs.probno", ondelete="cascade"), nullable=False
    )
    userid = db.Column(db.Integer, db.ForeignKey("users.uid", ondelete="cascade"))
    answer = db.Column(db.Text, nullable=False)
    ispassed = db.Column(db.Boolean)
    score = db.Column(db.Integer)
    timestamp = db.Column(
        db.DateTime,
        default=db.func.utc_timestamp(),
        server_default=db.func.utc_timestamp(),
    )

    def __lt__(self, sub):
        return self.probno < sub.probno


class ProbSolution(db.Model):
    __tablename__ = "solutions"
    probno = db.Column(
        db.String(16),
        db.ForeignKey("probs.probno", ondelete="cascade"),
        primary_key=True,
    )
    solno = db.Column(db.Integer, primary_key=True)
    userid = db.Column(db.Integer, db.ForeignKey("users.uid", ondelete="set null"))
    title = db.Column(db.String(128), nullable=False)
    content = db.Column(db.Text, nullable=False)
    timestamp = db.Column(
        db.DateTime,
        default=db.func.utc_timestamp(),
        server_default=db.func.utc_timestamp(),
    )
    post_type = 1

    def get_post_ident(self):
        return list2csv([self.probno, self.solno])

    def get_toplevel_comments(self):
        post_ident = self.get_post_ident()
        return (
            Comment.query.filter(
                Comment.post_type == 1,
                Comment.post_ident == post_ident,
                Comment.replyto_id.is_(None),
            )
            .order_by(Comment.timestamp.desc())
            .all()
        )

    def edit(self, title, content):
        if title:
            self.title = title
        if content:
            self.content = content
        db.session.commit()

    def viewable_for(self, user):
        return self.prob.viewable_for(user) or user == self.user

    def editable_for(self, user):
        return user.is_authenticated and (user == self.user or user.isadmin)

    def __str__(self):
        return f"问题 {self.probno} 的题解：{self.title}"

    def __lt__(self, solution):
        return self.probno < solution.probno


class Tag(db.Model):
    __tablename__ = "tags"
    tagtitle = db.Column(db.String(16), primary_key=True)
    probs = db.relationship(
        "Prob", secondary=prob_tag, back_populates="tags", collection_class=set
    )

    def rename(self, new_title):
        if not new_title:
            return False, "Empty tag title."
        target_tag = get_tag(new_title)
        if target_tag is not None:
            return self.merge_with(target_tag)
        self.tagtitle = new_title
        db.session.commit()
        return True, self

    def merge_with(self, target_tag):
        if not isinstance(target_tag, Tag):
            return False, "Target tag not found."
        for prob in list(self.probs):
            prob.tags.remove(self)
            prob.tags.add(target_tag)
        db.session.delete(self)
        db.session.commit()
        return True, target_tag


def get_post(post_type, post_ident):
    if post_type == 0:
        return get_prob(post_ident)
    if post_type == 1:
        try:
            probno, solno = csv2list(post_ident)
        except Exception:
            return None
        return get_solution(probno, int(solno))
    if post_type == 3:
        return get_article(int(post_ident))
    return None


def get_prob(probno: str):
    return db.session.get(Prob, str(probno))


def add_prob(**kwargs):
    probno = kwargs.get("probno")
    probtitle = kwargs.get("probtitle")
    statement = kwargs.get("statement")
    if not probtitle:
        return False, "Empty title."
    elif not statement:
        return False, "Empty statement of the problem."
    elif get_prob(probno) is not None:
        return False, f"Problem {probno} already exists."
    prob = Prob(**kwargs)
    db.session.add(prob)
    db.session.commit()
    return True, prob


def get_solution(probno, solno):
    return db.session.get(ProbSolution, (str(probno), int(solno)))


def add_solution(user, probno, title, content):
    if not title:
        return False, "Empty title."
    elif not content:
        return False, "Empty content."
    prob = get_prob(probno)
    if not prob:
        return False, "Problem not found."
    solution = ProbSolution(
        prob=prob,
        solno=len(prob.solutions),
        user=user,
        title=title,
        content=content,
    )
    db.session.add(solution)
    db.session.commit()
    return True, solution


def get_tag(tagtitle, create=False):
    tag = db.session.get(Tag, str(tagtitle))
    if create and tag is None:
        tag = Tag(tagtitle=str(tagtitle))
        db.session.add(tag)
        db.session.commit()
    return tag


def add2tags(tagtitles, prob):
    for tagtitle in set(tagtitles):
        tag = get_tag(tagtitle, create=True)
        tag.probs.add(prob)
    db.session.commit()


# =========================== 专栏数据库 ===========================


class Article(db.Model):
    __tablename__ = "articles"
    id = db.Column(db.Integer, primary_key=True)
    userid = db.Column(db.Integer, db.ForeignKey("users.uid", ondelete="set null"))
    title = db.Column(db.String(128), nullable=False)
    content = db.Column(db.Text, nullable=False)
    timestamp = db.Column(
        db.DateTime,
        default=db.func.utc_timestamp(),
        server_default=db.func.utc_timestamp(),
    )
    post_type = 3

    def get_post_ident(self):
        return str(self.id)

    def get_toplevel_comments(self):
        post_ident = self.get_post_ident()
        return (
            Comment.query.filter(
                Comment.post_type == 3,
                Comment.post_ident == post_ident,
                Comment.replyto_id.is_(None),
            )
            .order_by(Comment.timestamp.desc())
            .all()
        )

    def edit(self, title, content):
        if title:
            self.title = title
        if content:
            self.content = content
        db.session.commit()

    def viewable_for(self, user):
        return True

    def editable_for(self, user):
        return user.is_authenticated and (user == self.user or user.isadmin)

    def __str__(self):
        return f"专栏：{self.title}"

    def __lt__(self, article):
        return self.id < article.id


def get_article(article_id):
    return db.session.get(Article, int(article_id))


def add_article(user, title, content):
    if not title:
        return False, "Empty title."
    elif not content:
        return False, "Empty content."
    article = Article(user=user, title=title, content=content)
    db.session.add(article)
    db.session.commit()
    return True, article


# =========================== 讨论区与私信数据库支持 ===========================


user_chat = db.Table(
    "user_chats",
    db.Column(
        "uid_receiver",
        db.Integer,
        db.ForeignKey("users.uid", ondelete="cascade"),
        primary_key=True,
    ),
    db.Column(
        "uid_sender",
        db.Integer,
        db.ForeignKey("users.uid", ondelete="cascade"),
        primary_key=True,
    ),
    db.Column(
        "lastvisit",
        db.DateTime,
        default=datetime.datetime(1000, 1, 1).replace(tzinfo=datetime.UTC),
        server_default=db.text("'1000-01-01 00:00:00'"),
    ),
)


def get_chatlastvisit(uid_receiver, uid_sender):
    result = db.session.execute(
        user_chat.select().where(
            user_chat.c.uid_receiver == uid_receiver,
            user_chat.c.uid_sender == uid_sender,
        )
    ).first()
    if result is None:
        db.session.execute(
            user_chat.insert().values(uid_receiver=uid_receiver, uid_sender=uid_sender)
        )
        result = db.session.execute(
            user_chat.select().where(
                user_chat.c.uid_receiver == uid_receiver,
                user_chat.c.uid_sender == uid_sender,
            )
        ).first()
        db.session.commit()
    return result


def update_chatlastvisit(uid_receiver, uid_sender):
    exists = get_chatlastvisit(uid_receiver, uid_sender)
    if not exists:
        db.session.execute(
            user_chat.insert().values(
                uid_receiver=uid_receiver, uid_sender=uid_sender, lastvisit=_utcnow()
            )
        )
    else:
        db.session.execute(
            user_chat.update()
            .where(
                user_chat.c.uid_receiver == uid_receiver,
                user_chat.c.uid_sender == uid_sender,
            )
            .values(lastvisit=_utcnow())
        )
    db.session.commit()


class Comment(db.Model):
    __tablename__ = "comments"
    cmtid = db.Column(db.Integer, primary_key=True)
    uid = db.Column(db.Integer, db.ForeignKey("users.uid", ondelete="set null"))
    content = db.Column(db.Text)
    timestamp = db.Column(
        db.DateTime,
        default=db.func.utc_timestamp(),
        server_default=db.func.utc_timestamp(),
    )
    replyto_id = db.Column(
        db.Integer, db.ForeignKey("comments.cmtid", ondelete="set null")
    )
    # 帖子类型为0，帖子为题目，标识符为题目编号
    # 帖子类型为1，帖子为题解，标识符为CSV格式的题目编号与题解编号的组合
    # 帖子类型为2，帖子为私信，标识符为信息接收用户ID，不使用replyto、replies字段
    # 帖子类型为3，帖子为专栏，标识符为专栏ID
    post_type = db.Column(db.Integer, nullable=False)  # 帖子类型
    post_ident = db.Column(db.String(64), nullable=False)  # 帖子标识符
    replyto = db.relationship("Comment", back_populates="replies", remote_side=[cmtid])
    replies = db.relationship(
        "Comment", back_populates="replyto", cascade="all, delete"
    )

    def get_all_replies(self):
        return sorted(
            sum(
                [comment.get_all_replies() for comment in self.replies],
                start=self.replies.copy(),
            )
        )

    def get_post(self):
        return get_post(self.post_type, self.post_ident)

    def editable_for(self, user):
        return user.is_authenticated and (user == self.user or user.isadmin)

    def __lt__(self, comment):
        return self.timestamp < comment.timestamp


def get_comment(commentid):
    return db.session.get(Comment, int(commentid))


def clear_comments(post):
    for comment in post.get_toplevel_comments():
        db.session.delete(comment)
    db.session.commit()
