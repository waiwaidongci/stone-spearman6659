from sqlalchemy import Column,Integer,String,Float,JSON,Text,ForeignKey,UniqueConstraint
from src.config.database import Base
class MatchRun(Base):
    __tablename__='match_runs'
    id=Column(Integer,primary_key=True)
    name=Column(String(120),nullable=False)
    test_study_id=Column(Integer,ForeignKey('studies.id'),nullable=False)
    control_study_id=Column(Integer,ForeignKey('studies.id'),nullable=False)
    tolerance=Column(Float,nullable=False)
    status=Column(String(20),default='queued')
    snapshot=Column(JSON,nullable=False)
    checksum=Column(String(64),nullable=False)
    expected_pairs=Column(Integer,default=0)
    result=Column(JSON,nullable=True)
    error=Column(Text,default='')
    created_at=Column(String(40),nullable=False)
class MatchPair(Base):
    __tablename__='match_pairs'
    __table_args__=(UniqueConstraint('run_id','pair_index'),UniqueConstraint('run_id','test_key'),UniqueConstraint('run_id','control_key'))
    id=Column(Integer,primary_key=True)
    run_id=Column(Integer,ForeignKey('match_runs.id'),nullable=False)
    pair_index=Column(Integer,nullable=False)
    test_key=Column(String(100),nullable=False)
    control_key=Column(String(100),nullable=False)
    test_porosity=Column(Float,nullable=False)
    control_porosity=Column(Float,nullable=False)
    porosity_diff=Column(Float,nullable=False)
    test_absorption=Column(Float,nullable=False)
    control_absorption=Column(Float,nullable=False)
    absorption_diff=Column(Float,nullable=False)
