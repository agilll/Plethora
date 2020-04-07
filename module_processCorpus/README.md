Subproject to process original corpus files downloaded from Internet and generate .t files

Depends on px_aux, px_aux_add_suffix, px_DB_Manager of the main project


They are executed in order to finally generate .t files:

1 - add suffixes to identified names (input .txt, output .txt.s)
    The actual job of changing contents is done by the external 
    processContent() function, shared with the main project

    python3 1AddSuffixToTexts.py folder 

2 - build DB entities file (input .s, output .s.p)

    python3 2BuildDbpediaInfoFromTexts.py folder

3 - change surface forms by entity names (input .s and .p, output .s.w)

    python3 3UpdateTextsEntities.py folder

4 - remove stopwords and tokenize (input .w, output .t)
    Requires the Stanford Core NLP server to be started and listening in port 9000

    python3 4tokenize.py folder
