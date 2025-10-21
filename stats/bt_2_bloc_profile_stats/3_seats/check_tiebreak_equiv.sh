#!/usr/bin/env bash

for f in $(find . -type f -name "*lex.json"); do
    other=${f/lex.json/random.json}
    if [[ ! -f $other ]]; then
        echo "File $other does not exist!"
        exit 1
    fi
    cmp "$f" "$other"
    if [[ $? -ne 0 ]]; then
        echo "Files $f and $other differ!"
        echo
        cat $f
        echo
        echo
        cat $other
        exit 1
    fi
    echo $f
done

