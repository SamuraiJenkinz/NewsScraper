"""
Excel import/export service for BrasilIntel.

Provides Excel file parsing with column normalization, validation,
and data extraction following research-backed patterns:
- Pitfall 2: Explicit missing value handling
- Pitfall 6: Flexible column name matching

Supports DATA-04 (upload Excel), DATA-05 (preview before commit),
DATA-07 (validate required fields), DATA-08 (reject duplicates).
"""
import pandas as pd
from io import BytesIO
from typing import BinaryIO

from app.schemas.insurer import InsurerCreate


# Column name mapping for flexible matching
# Supports both English and Portuguese column headers
COLUMN_MAP = {
    'ans_code': [
        'ans_code', 'anscode', 'ans code', 'ans', 'code', 'codigo_ans',
        'codigo ans', 'registro_ans', 'registro ans'
    ],
    'name': [
        'insurer_name', 'name', 'company_name', 'insurer name', 'razao_social',
        'razao social', 'nome', 'operadora', 'nome_operadora'
    ],
    'cnpj': [
        'company_registration_number', 'cnpj', 'registration', 'cpf_cnpj',
        'cnpj_operadora', 'documento'
    ],
    'category': [
        'product', 'category', 'type', 'produto', 'modalidade', 'segmento',
        'tipo', 'natureza'
    ],
    'market_master': [
        'market_master', 'market master', 'marketmaster', 'grupo', 'grupo_economico',
        'grupo economico', 'holding', 'controladora'
    ],
    'status': [
        'status', 'situacao', 'situacao_registro', 'status_operadora', 'ativa'
    ]
}

# Category normalization mapping (Portuguese to English standard)
CATEGORY_MAP = {
    # Portuguese variants
    'saude': 'Health',
    'saúde': 'Health',
    'medico hospitalar': 'Health',
    'médico hospitalar': 'Health',
    'medico-hospitalar': 'Health',
    'médico-hospitalar': 'Health',
    'hospitalar': 'Health',
    'odontologico': 'Dental',
    'odontológico': 'Dental',
    'odonto': 'Dental',
    'dental': 'Dental',
    'vida': 'Group Life',
    'vida em grupo': 'Group Life',
    'group life': 'Group Life',
    'seguro de vida': 'Group Life',
    # English variants
    'health': 'Health',
    'group life': 'Group Life',
}


def normalize_columns(df: pd.DataFrame) -> pd.DataFrame:
    """
    Normalize column names for flexible matching.

    Handles variations in column naming between different Excel exports:
    - Strips whitespace
    - Converts to lowercase
    - Replaces spaces with underscores
    - Maps variants to standard names

    Args:
        df: DataFrame with original column names

    Returns:
        DataFrame with normalized column names
    """
    # Clean column names
    df.columns = (
        df.columns
        .str.strip()
        .str.lower()
        .str.replace(' ', '_', regex=False)
        .str.replace('-', '_', regex=False)
    )

    # Create reverse mapping: variant -> standard name
    column_renames = {}
    for standard, variants in COLUMN_MAP.items():
        for variant in variants:
            normalized_variant = variant.lower().replace(' ', '_').replace('-', '_')
            if normalized_variant in df.columns:
                column_renames[normalized_variant] = standard
                break  # Use first match for this standard name

    # Apply renames
    df = df.rename(columns=column_renames)

    return df


def normalize_category(category: str) -> str:
    """
    Normalize category to standard values (Health, Dental, Group Life).

    Args:
        category: Raw category string from Excel

    Returns:
        Normalized category string

    Raises:
        ValueError: If category cannot be mapped
    """
    if not category:
        raise ValueError("Category is required")

    normalized = category.strip().lower()
    if normalized in CATEGORY_MAP:
        return CATEGORY_MAP[normalized]

    # If already a valid category, return as-is
    valid_categories = {'Health', 'Dental', 'Group Life'}
    if category.strip() in valid_categories:
        return category.strip()

    raise ValueError(f"Invalid category: '{category}'. Must be Health, Dental, or Group Life")


def parse_excel_insurers(file: BinaryIO) -> tuple[list[dict], list[dict]]:
    """
    Parse Excel file and validate insurer rows.

    Implements research-backed patterns:
    - Explicit missing value handling (Pitfall 2)
    - Flexible column matching (Pitfall 6)
    - Pydantic validation for type safety

    Args:
        file: File-like object containing Excel data

    Returns:
        Tuple of (validated_rows, errors) where:
        - validated_rows: List of dicts ready for InsurerCreate
        - errors: List of dicts with row numbers and error messages
    """
    # Read Excel with explicit missing value handling (Pitfall 2)
    try:
        df = pd.read_excel(
            file,
            engine='openpyxl',
            na_values=['', 'NA', 'N/A', 'null', 'Nil', '?', 'nan', 'NaN', '-', '--'],
            keep_default_na=True
        )
    except Exception as e:
        return [], [{'row': 0, 'ans_code': 'N/A', 'error': f'Failed to read Excel file: {str(e)}'}]

    # Handle empty file
    if df.empty:
        return [], [{'row': 0, 'ans_code': 'N/A', 'error': 'Excel file is empty'}]

    # Normalize column names
    df = normalize_columns(df)

    # Check for required columns
    required_columns = ['ans_code', 'name', 'category']
    missing_columns = [col for col in required_columns if col not in df.columns]
    if missing_columns:
        return [], [{
            'row': 0,
            'ans_code': 'N/A',
            'error': f"Missing required columns: {', '.join(missing_columns)}"
        }]

    # Fill missing optional fields with empty strings
    optional_columns = ['cnpj', 'market_master', 'status']
    for col in optional_columns:
        if col not in df.columns:
            df[col] = ''
        else:
            df[col] = df[col].fillna('')

    validated = []
    errors = []

    for idx, row in df.iterrows():
        row_num = idx + 2  # Excel row (1-indexed + header row)

        try:
            # Handle ANS code - convert to string, handle floats from Excel
            ans_code = row.get('ans_code')
            if pd.isna(ans_code) or ans_code == '':
                errors.append({
                    'row': row_num,
                    'ans_code': 'N/A',
                    'error': 'ANS code is required'
                })
                continue

            # Convert to string, handle float representation
            if isinstance(ans_code, float):
                ans_code = str(int(ans_code))
            else:
                ans_code = str(ans_code).strip()

            # Pad to 6 digits if needed
            ans_code = ans_code.zfill(6)

            # Validate name
            name = row.get('name')
            if pd.isna(name) or str(name).strip() == '':
                errors.append({
                    'row': row_num,
                    'ans_code': ans_code,
                    'error': 'Name is required'
                })
                continue

            # Normalize category
            raw_category = row.get('category')
            if pd.isna(raw_category) or str(raw_category).strip() == '':
                errors.append({
                    'row': row_num,
                    'ans_code': ans_code,
                    'error': 'Category is required'
                })
                continue

            try:
                category = normalize_category(str(raw_category))
            except ValueError as e:
                errors.append({
                    'row': row_num,
                    'ans_code': ans_code,
                    'error': str(e)
                })
                continue

            # Build insurer data
            insurer_data = {
                'ans_code': ans_code,
                'name': str(name).strip(),
                'cnpj': str(row.get('cnpj', '')).strip() or None,
                'category': category,
                'market_master': str(row.get('market_master', '')).strip() or None,
                'status': str(row.get('status', '')).strip() or None,
            }

            # Validate with Pydantic
            insurer = InsurerCreate(**insurer_data)
            validated.append(insurer.model_dump())

        except Exception as e:
            errors.append({
                'row': row_num,
                'ans_code': str(row.get('ans_code', 'N/A')),
                'error': str(e)
            })

    return validated, errors


def generate_excel_export(insurers: list[dict]) -> bytes:
    """
    Generate Excel file from insurer data.

    Args:
        insurers: List of insurer dictionaries

    Returns:
        Excel file as bytes
    """
    df = pd.DataFrame(insurers)

    # Reorder columns for export
    column_order = [
        'ans_code', 'name', 'cnpj', 'category', 'market_master',
        'status', 'enabled', 'search_terms', 'created_at', 'updated_at'
    ]
    # Keep only columns that exist
    columns = [c for c in column_order if c in df.columns]
    df = df[columns]

    # Write to bytes
    output = BytesIO()
    df.to_excel(output, index=False, engine='openpyxl')
    output.seek(0)

    return output.read()
