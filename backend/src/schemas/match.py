from pydantic import BaseModel,Field
class MatchRunInput(BaseModel):
    name:str=Field(min_length=2,max_length=120)
    test_study_id:int=Field(gt=0)
    control_study_id:int=Field(gt=0)
    tolerance:float=Field(ge=0,le=100)
