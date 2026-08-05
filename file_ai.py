import os
from pypdf import PdfReader



def read_file(path):

    try:

        if path.endswith(".txt"):

            with open(
                path,
                "r",
                encoding="utf-8"
            ) as f:

                return f.read()



        elif path.endswith(".pdf"):

            reader = PdfReader(path)

            text = ""

            for page in reader.pages:

                text += page.extract_text()


            return text



        else:

            return "I can't read this file type yet."


    except Exception as e:

        print("FILE ERROR:", e)

        return "File reading failed."