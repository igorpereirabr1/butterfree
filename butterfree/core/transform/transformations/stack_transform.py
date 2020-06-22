"""Stack Transform entity."""

import re
from typing import List

from pyspark.sql import DataFrame
from pyspark.sql.functions import array, explode

from butterfree.core.transform.transformations.transform_component import (
    TransformComponent,
)


class StackTransform(TransformComponent):
    """Defines a Stack transformation.

    For instantiation it is needed the name of the columns or a pattern to use
    to find the columns that need to be stacked. This transform generates just
    one column as output.

    Attributes:
        columns_names: full names or patterns to search for target columns on
            the dataframe.
            By default a single `*` character is considered a wildcard and can
            be anywhere in the string, multiple wildcards are not supported.
            Strings can also start with an `!` (exclamation mark), it indicates
            a negation, be it a regular string or simple pattern.
            When parameter :param is_regex: is `True`, simple patterns wildcards
            and negation are disabled and all strings are interpreted as regular
            expressions.

        is_regex: boolean flag to indicate if columns_names passed are a Python
            regex string patterns.

    Example:
        >>> from pyspark import SparkContext
        >>> from pyspark.sql import session
        >>> from butterfree.testing.dataframe import create_df_from_collection
        >>> from butterfree.core.transform.transformations import StackTransform
        >>> from butterfree.core.transform.features import Feature
        >>> spark_context = SparkContext.getOrCreate()
        >>> spark_session = session.SparkSession(spark_context)
        >>> data = [
        ...    {"feature": 100, "id_a": 1, "id_b": 2},
        ...    {"feature": 120, "id_a": 3, "id_b": 4},
        ... ]
        >>> df = create_df_from_collection(data, spark_context, spark_session)
        >>> df.collect()
        [Row(feature=100, id_a=1, id_b=2), Row(feature=120, id_a=3, id_b=4)]
        >>> feature = Feature(
        ...     name="stack_ids",
        ...     description="id_a and id_b stacked in a single column.",
        ...     transformation=StackTransform("id_a", "id_b"),
        ... )
        >>> feature.transform(df).collect()
        [
            Row(feature=100, id_a=1, id_b=2, stack_ids=1),
            Row(feature=100, id_a=1, id_b=2, stack_ids=2),
            Row(feature=120, id_a=3, id_b=4, stack_ids=3),
            Row(feature=120, id_a=3, id_b=4, stack_ids=4)
        ]

        The StackTransform can be instantiated using a column pattern instead of
        the columns full names. Like this way:

        >>> feature = Feature(
        ...     name="stack_ids",
        ...     description="id_a and id_b stacked in a single column.",
        ...     transformation=StackTransform(columns_prefix="id_*"),
        ... )

    """

    def __init__(self, *columns_names: str, is_regex: bool = False):
        super().__init__()
        self.columns_names = columns_names
        self.regex_enabled = is_regex

    @property
    def output_columns(self) -> List[str]:
        """Columns generated by the transformation."""
        return self._parent.name

    def _matches_pattern(self, pattern: str, column: str) -> bool:
        """Verify if the column name matches the pattern.

        Args:
            pattern: string pattern to use.
            column: column names to try match with the pattern.

        Returns:
            True for a column that matches the pattern, False otherwise.

        """
        if self.regex_enabled:
            return bool(re.match(pattern, column))
        negate = False
        if pattern.startswith("!"):
            negate = True
            pattern = pattern[1:]
        split = pattern.split("*")
        matches_pattern = column.startswith(split[0]) and column.endswith(split[-1])
        return matches_pattern if not negate else not matches_pattern

    def transform(self, dataframe: DataFrame) -> DataFrame:
        """Performs a transformation to the feature pipeline.

        Args:
            dataframe: input dataframe.

        Returns:
            Transformed dataframe.

        """
        columns = [
            column
            for column in dataframe.columns
            if any(
                self._matches_pattern(pattern, column) for pattern in self.columns_names
            )
        ]

        if not columns:
            raise ValueError(
                "Columns not found, columns in df: {}".format(dataframe.columns)
            )

        return dataframe.withColumn(self._parent.name, explode(array(*columns)))
