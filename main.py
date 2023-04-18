import streamlit as st
import pandas as pd
import numpy as np
from sqlalchemy import create_engine, Column, Integer, String, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, sessionmaker
from sqlalchemy.exc import OperationalError

Base = declarative_base()

SQLALCHEMY_DATABASE_URL = "sqlite:///mycourse_data5.db"

class Course(Base):
    __tablename__ = "courses"

    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    total_votes = Column(Integer, nullable=False, default=100)
    group_num = Column(Integer, nullable=False, default=10)
    time_slots = relationship("TimeSlot", back_populates="course")
    topics = relationship("Topic", back_populates="course")
    groups = relationship("Group", back_populates="course")

class TimeSlot(Base):
    __tablename__ = "time_slots"

    id = Column(Integer, primary_key=True)
    begin = Column(String, nullable=False)
    end = Column(String, nullable=False)
    course_id = Column(Integer, ForeignKey("courses.id"))

    course = relationship("Course", back_populates="time_slots")
    time_slot_votes = relationship("TimeSlotVote", back_populates="time_slot")

class Topic(Base):
    __tablename__ = "topics"

    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    description = Column(String, nullable=True)
    course_id = Column(Integer, ForeignKey("courses.id"))

    course = relationship("Course", back_populates="topics")
    topic_votes = relationship("TopicVote", back_populates="topic")

class Group(Base):
    __tablename__ = "groups"

    id = Column(Integer, primary_key=True)
    course_id = Column(Integer, ForeignKey("courses.id"))

    course = relationship("Course", back_populates="groups")
    time_slot_votes = relationship("TimeSlotVote", back_populates="group")
    topic_votes = relationship("TopicVote", back_populates="group")

class TimeSlotVote(Base):
    __tablename__ = "time_slot_votes"

    id = Column(Integer, primary_key=True)
    group_id = Column(Integer, ForeignKey("groups.id"))
    time_slot_id = Column(Integer, ForeignKey("time_slots.id"))
    vote_count = Column(Integer, nullable=False, default=0)

    group = relationship("Group", back_populates="time_slot_votes")
    time_slot = relationship("TimeSlot", back_populates="time_slot_votes")

class TopicVote(Base):
    __tablename__ = "topic_votes"

    id = Column(Integer, primary_key=True)
    group_id = Column(Integer, ForeignKey("groups.id"))
    topic_id = Column(Integer, ForeignKey("topics.id"))
    vote_count = Column(Integer, nullable=False, default=0)

    group = relationship("Group", back_populates="topic_votes")
    topic = relationship("Topic", back_populates="topic_votes")

def normalize_votes(votes):
    total_votes = sum(votes)
    if total_votes == 0:
        return votes
    return [vote / total_votes for vote in votes]


def add_course(engine):
    st.markdown("## Course Settings")
    course_name = st.text_input("Course Name")
    total_votes = st.number_input("Total Votes", min_value=50, max_value=1000, value=100)
    group_num = st.number_input("Group Number", min_value=3, max_value=100)
    st.markdown("## Time Slots")
    timeslots_empty = pd.DataFrame([{'begin': '1pm', 'end': '2pm'}], columns=['begin', 'end'])
    timeslots = st.experimental_data_editor(timeslots_empty, num_rows="dynamic")
    st.markdown("## Topics")
    topics_empty = pd.DataFrame([{'name': 'ABM', 'description': ''}], columns=['name', 'description'])
    topics = st.experimental_data_editor(topics_empty, num_rows="dynamic")

    if st.button('Submit'):
        try:
            Base.metadata.create_all(engine)
        except OperationalError:
            pass
        Session = sessionmaker(bind=engine)
        session = Session()

        new_course = Course(name=course_name, total_votes=total_votes, group_num=group_num)

        for begin, end in timeslots.values:
            time_slot_item = TimeSlot(begin=begin, end=end)
            time_slot_item.course = new_course
            session.add(time_slot_item)

        for name, description in topics.values:
            topic_item = Topic(name=name, description=description)
            topic_item.course = new_course
            session.add(topic_item)

        for group in range(group_num):
            new_group = Group(course_id=new_course.id)
            new_group.course = new_course
            session.add(new_group)

        session.add(new_course)
        
        session.commit()
        st.success("Course added successfully!")
        session.close()

def vote(engine):
    course_name = st.sidebar.text_input("Course Name")
    group_id = st.sidebar.text_input("Group ID")
    st.session_state['course_name'] = course_name
    st.session_state['group_id'] = group_id
    if 'course_name' in st.session_state.keys() or  st.sidebar.button("Start"):
        # Create a session
        Session = sessionmaker(bind=engine)
        session = Session()
        course = session.query(Course).filter(Course.name == course_name).all()[0]
        st.title(course.name)
        st.markdown("## Time Slots")
        timeslots_base = pd.DataFrame([[time_slot.id, 0, time_slot.begin, time_slot.end] for time_slot in course.time_slots], columns=['id', 'votes', 'begin', 'end'])
        timeslots = st.experimental_data_editor(timeslots_base)
        st.markdown("## Topics")
        topics_base = pd.DataFrame([[topic.id, 0, topic.name, topic.description] for topic in course.topics], columns=['id', 'votes', 'name', 'description'])
        topics = st.experimental_data_editor(topics_base)

        if st.button('Submit'):
            # Check whether votes in timeslots & topics all sums up to course.total_votes
            if timeslots['votes'].sum() != course.total_votes:
                st.error("The sum of votes in time slots does not equal to total votes.")
            elif topics['votes'].sum() != course.total_votes:
                st.error("The sum of votes in topics does not equal to total votes.")
            else:
                # Update database
                group = session.query(Group).filter(Group.id == group_id).one()
                # Add time slot votes
                for index, row in timeslots.iterrows():
                    time_slot_id = row['id']
                    vote_count = row['votes']
                    time_slot_vote = TimeSlotVote(group_id=group.id, time_slot_id=time_slot_id, vote_count=vote_count)
                    time_slot_vote.time_slot = session.query(TimeSlot).filter(TimeSlot.id == (index + 1)).one()
                    group.time_slot_votes.append(time_slot_vote)

                # Add topic votes
                for index, row in topics.iterrows():
                    topic_id = row['id']
                    vote_count = row['votes']
                    topic_vote = TopicVote(group_id=group.id, topic_id=topic_id, vote_count=vote_count)
                    topic_vote.topic = session.query(Topic).filter(Topic.id == (index + 1)).one()
                    group.topic_votes.append(topic_vote)

                session.commit()
                session.close()
                st.success("Votes submitted successfully.")

def results(engine):
    st.sidebar.title("Results")
    course_name = st.sidebar.text_input("Course Name")

    if st.sidebar.button("Start"):
        # Create a session
        Session = sessionmaker(bind=engine)
        session = Session()
        
        course = session.query(Course).filter(Course.name == course_name).all()[0]

        st.title(course.name)

        votes = {}

        # Iterate through the groups associated with the course
        for group in course.groups:
            group_id = group.id

            # Get topic votes for the group
            topic_votes = [0] * len(course.topics)
            for topic_vote in group.topic_votes:
                index = course.topics.index(topic_vote.topic)
                topic_votes[index] = topic_vote.vote_count
            normalized_topic_votes = normalize_votes(topic_votes)

            # Get time slot votes for the group
            time_slot_votes = [0] * len(course.time_slots)
            for time_slot_vote in group.time_slot_votes:
                index = course.time_slots.index(time_slot_vote.time_slot)
                time_slot_votes[index] = time_slot_vote.vote_count
            normalized_time_slot_votes = normalize_votes(time_slot_votes)
            votes[group_id] = (normalized_topic_votes, normalized_time_slot_votes)
        
        n = len(course.groups)

        session.close()
        
        result = {}
        topics = [-1 for i in range(n)]
        slots = [-1 for i in range(n)]

        # filter most popular topics and time slots
        vt_list = [] # vote for topics
        vs_list = [] # vote for time slots
        for i, (vt, vs) in votes.items():
            vt_list.append(np.array(vt))
            vs_list.append(np.array(vs))
        vt_sum = sum(vt_list)
        popular_topics = np.argpartition(vt_sum, -n)[-n:]
        vs_sum = sum(vs_list)
        popular_slots = np.argpartition(vs_sum, -n)[-n:]

        # assign topic and time slots according to vote
        for t in popular_topics:
            vote = [vt_list[i][t] for i in range(n)]
            rank = sorted(zip(vote, range(n)), reverse=True)
            for v, i in rank:
                if topics[i] == -1:
                    topics[i] = t
                    break
        for s in popular_slots:
            vote = [vs_list[i][s] for i in range(n)]
            rank = sorted(zip(vote, range(n)), reverse=True)
            for v, i in rank:
                if slots[i] == -1:
                    slots[i] = s
                    break
            
        for i, (t, s) in enumerate(zip(topics, slots)):
            result[i + 1] = (t, s)

        for group in course.groups:
            group_id = group.id
            topic = course.topics[result[group_id][0]]
            time_slot = course.time_slots[result[group_id][1]]
            st.write(f"Group {group_id}: {topic.name} ({topic.description}) at {time_slot.begin}~{time_slot.end}")

st.sidebar.title("Topic & Timeslot Voting App")
option = st.sidebar.selectbox("Select an option", ["Add a Course", "Vote on a Course", "View Results", "Options"])
engine = create_engine(SQLALCHEMY_DATABASE_URL)
if option == "Add a Course":
    add_course(engine)
elif option == "Vote on a Course":
    vote(engine)
elif option == "View Results":
    results(engine)
elif option == "Options":
    if st.button("Reset Database"):
        Base.metadata.drop_all(engine)
        Base.metadata.create_all(engine)
        st.success("Database reset successfully.")
    if st.button("Disconnect from Database"):
        engine.dispose()
        st.success("Disconnected from database successfully.")
