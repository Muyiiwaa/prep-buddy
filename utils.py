from typing import List,Dict,Tuple
import instructor
import google.generativeai as genai
from pydantic import BaseModel,Field,field_validator
from dotenv import load_dotenv
from prompt import question_prompt
import os


load_dotenv()

GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
genai.configure(api_key=GOOGLE_API_KEY)


class Questions(BaseModel):
    questions: Dict[str, Tuple[List[str], str]] = Field(..., 
                                      description="Dictionary of questions and four multiple choice options for each of questions")
    
    @field_validator('questions')
    def check_answer_validity(cls, question_dict):
        for question, (options, correct_answer) in question_dict.items():
            if correct_answer not in options:
                raise ValueError(f'In Question {question} correct answer {correct_answer} not in list of options {options}')
        
        return question_dict
    

def get_question(num_question: int, notes: str) -> Dict:
    client = instructor.from_gemini(
        client=genai.GenerativeModel(
            model_name="models/gemini-1.5-flash-latest",
        ),
        mode=instructor.Mode.GEMINI_JSON,
    )

    # note that client.chat.completions.create will also work
    response = client.chat.completions.create(
        messages=[
                {"role": "system","content": f"{question_prompt(num_question)}"},
                {"role": "user", "content": f"{notes}"}
                
        ],
        response_model=Questions,
    )
    return response.questions


if __name__ == "__main__":
    note = input('Enter note: ')
    result = get_question(notes=note, num_question=5)
    print(result)