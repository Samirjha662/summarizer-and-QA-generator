import google.generativeai as genai

genai.configure(api_key="AIzaSyAgOreoKHFSymDsObmiKGB-LsFIO3pZEvA")

models = genai.list_models()

for m in models:
    print(m.name)
