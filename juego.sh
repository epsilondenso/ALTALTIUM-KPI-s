#!/bin/bash
# Juego de adivinar un número entre 1 y 100

numero=$(( RANDOM % 100 + 1 ))
intentos=0

echo "¡Bienvenido al juego de adivinar el número!"
echo "He pensado un número entre 1 y 100."

while true; do
    if ! read -p "Introduce tu intento: " intento; then
        echo
        echo "Juego terminado. El número era $numero."
        exit 1
    fi

    # Validar que sea un número entero entre 1 y 100
    if ! [[ "$intento" =~ ^[0-9]+$ ]] || (( intento < 1 || intento > 100 )); then
        echo "Por favor, introduce un número válido entre 1 y 100."
        continue
    fi

    intentos=$(( intentos + 1 ))

    if (( intento < numero )); then
        echo "El número es mayor."
    elif (( intento > numero )); then
        echo "El número es menor."
    else
        echo "¡Correcto! El número era $numero. Lo adivinaste en $intentos intentos."
        break
    fi
done
