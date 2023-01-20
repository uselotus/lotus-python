datamodel-codegen --url https://raw.githubusercontent.com/uselotus/lotus/main/docs/openapi.yaml --output ./lotus/models.py --strict-nullable
if [ "$1" == "--patch" ]; then
  bump2version patch
elif [ "$1" == "--minor" ]; then
  bump2version minor
elif [ "$1" == "--major" ]; then
  bump2version major
else
  echo "Invalid argument. Use --patch, --minor, or --major."
fi