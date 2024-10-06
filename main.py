from fastapi.exceptions import ResponseValidationError
import onnxruntime_genai as og
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sse_starlette.sse import EventSourceResponse


class Settings:
    ALLOW_ORIGINS = ["*"]  # Permite todas as origens. Alterar conforme necessário.

settings = Settings()

# Criação da aplicação FastAPI
app = FastAPI()

# Middleware CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOW_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class InputStreamRoute(BaseModel):
    query: str
    token: str

model = og.Model('cpu_and_mobile/cpu-int4-rtn-block-32-acc-level-4')
params = og.GeneratorParams(model)
tokenizer = og.Tokenizer(model)
tokenizer_stream = tokenizer.create_stream()
chat_template = '<|user|>\n{input} <|end|>\n<|assistant|>'

search_options = {
    'do_sample': False,
    'max_length': 2048
}

params.set_search_options(**search_options)

@app.post("/api/stream")
async def main(input: InputStreamRoute):
    # Configuração do modelo e tokenizer
    prompt = f'{chat_template.format(input=input.query)}'
    input_tokens = tokenizer.encode(prompt)
    params.input_ids = input_tokens
    token = "rU0r7XjSSvW1jxhS0b1L1Ulo0h5MmvEruGI1mSajM2TMesKF9KwKgkP17hYXiVfg"

    if (not input.token) or (input.token != token):
        return ResponseValidationError(["Invalid token"])
    # Criar o gerador do modelo
    generator = og.Generator(model, params)

    async def token_stream():
        # A função que envia os tokens conforme forem gerados
        try:
            while not generator.is_done():
                generator.compute_logits()
                generator.generate_next_token()
                new_token = generator.get_next_tokens()[0]
                decoded_token = tokenizer_stream.decode(new_token)
                
                # Enviar o token ao cliente
                yield {"data": decoded_token}
                

            # Quando o processamento acabar, enviar uma mensagem final
        except Exception as e:
            # Caso ocorra algum erro, você pode logar ou tratar aqui
            yield {"event": "error", "data": str(e)}

    return EventSourceResponse(token_stream())





