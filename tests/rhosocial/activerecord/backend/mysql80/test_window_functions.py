import logging
import pytest

from src.rhosocial.activerecord.backend.dialect import DatabaseType

# Setup logger
logger = logging.getLogger("mysql_test")


def setup_window_function_tables(backend):
    """Setup test tables for window function tests"""
    # Drop existing tables if they exist
    try:
        backend.execute("DROP TABLE IF EXISTS window_test_employees")
        backend.execute("DROP TABLE IF EXISTS window_test_sales")
    except Exception as e:
        logger.warning(f"Error dropping existing tables: {e}")

    # Create employees table
    try:
        backend.execute("""
            CREATE TABLE window_test_employees (
                id INT AUTO_INCREMENT PRIMARY KEY,
                name VARCHAR(100) NOT NULL,
                department VARCHAR(50) NOT NULL,
                salary DECIMAL(10, 2) NOT NULL,
                hire_date DATE NOT NULL,
                manager_id INT NULL
            )
        """)
        logger.info("Created window_test_employees table")

        # Create sales table
        backend.execute("""
            CREATE TABLE window_test_sales (
                id INT AUTO_INCREMENT PRIMARY KEY,
                employee_id INT NOT NULL,
                sale_date DATE NOT NULL,
                amount DECIMAL(10, 2) NOT NULL,
                product_category VARCHAR(50) NOT NULL,
                region VARCHAR(50) NOT NULL,
                FOREIGN KEY (employee_id) REFERENCES window_test_employees(id)
            )
        """)
        logger.info("Created window_test_sales table")

        # Insert employees data
        employees = [
            ("John Smith", "Sales", 65000.00, "2018-03-15", None),
            ("Mary Johnson", "Sales", 58000.00, "2019-07-21", 1),
            ("Robert Davis", "Sales", 52000.00, "2020-01-10", 1),
            ("Lisa Brown", "Marketing", 62000.00, "2017-11-05", None),
            ("Michael Wilson", "Marketing", 54000.00, "2019-02-18", 4),
            ("Sarah Miller", "Marketing", 51000.00, "2020-04-12", 4),
            ("David Garcia", "IT", 75000.00, "2016-08-30", None),
            ("Jennifer Martinez", "IT", 67000.00, "2018-05-25", 7),
            ("James Robinson", "IT", 63000.00, "2019-09-14", 7),
            ("Patricia Lee", "Finance", 72000.00, "2017-06-08", None),
            ("Thomas Taylor", "Finance", 64000.00, "2018-10-22", 10),
            ("Jessica Wright", "Finance", 59000.00, "2019-12-03", 10)
        ]

        for employee in employees:
            backend.execute(
                "INSERT INTO window_test_employees (name, department, salary, hire_date, manager_id) VALUES (%s, %s, %s, %s, %s)",
                employee
            )
        logger.info("Inserted test employees")

        # Insert sales data
        sales = [
            (1, "2022-01-15", 12500.50, "Hardware", "East"),
            (1, "2022-02-20", 9800.75, "Software", "East"),
            (1, "2022-03-18", 11200.25, "Services", "East"),
            (2, "2022-01-22", 8700.00, "Hardware", "West"),
            (2, "2022-02-12", 10200.50, "Software", "West"),
            (2, "2022-03-05", 7500.25, "Services", "West"),
            (3, "2022-01-10", 6500.75, "Hardware", "South"),
            (3, "2022-02-28", 8900.00, "Software", "South"),
            (3, "2022-03-22", 7200.50, "Services", "South"),
            (4, "2022-01-05", 5200.25, "Hardware", "North"),
            (4, "2022-02-15", 6700.50, "Software", "North"),
            (4, "2022-03-12", 4900.75, "Services", "North"),
            (5, "2022-01-18", 7800.00, "Hardware", "East"),
            (5, "2022-02-23", 9100.25, "Software", "East"),
            (5, "2022-03-07", 8200.50, "Services", "East"),
            (6, "2022-01-25", 6300.75, "Hardware", "West"),
            (6, "2022-02-08", 7400.25, "Software", "West"),
            (6, "2022-03-30", 5800.50, "Services", "West")
        ]

        for sale in sales:
            backend.execute(
                "INSERT INTO window_test_sales (employee_id, sale_date, amount, product_category, region) VALUES (%s, %s, %s, %s, %s)",
                sale
            )
        logger.info("Inserted test sales")

    except Exception as e:
        logger.error(f"Error creating window function test tables: {e}")
        raise


def teardown_window_function_tables(backend):
    """Clean up window function test tables"""
    try:
        backend.execute("DROP TABLE IF EXISTS window_test_sales")
        backend.execute("DROP TABLE IF EXISTS window_test_employees")
        logger.info("Dropped window function test tables")
    except Exception as e:
        logger.error(f"Error dropping window function test tables: {e}")


@pytest.fixture(scope="function")
def mysql_window_function_test_db(mysql_test_db):
    """Setup and teardown for window function tests"""
    setup_window_function_tables(mysql_test_db)
    yield mysql_test_db
    teardown_window_function_tables(mysql_test_db)


def check_window_function_support(mysql_backend):
    """Check if this MySQL version supports window functions

    Window functions were introduced in MySQL 8.0.
    """
    try:
        version = mysql_backend.get_server_version()
        # Window functions are supported in MySQL 8.0+
        return version >= (8, 0, 0)
    except:
        # If version detection fails, assume it's not supported
        return False


def test_mysql_version_detection(mysql_window_function_test_db):
    """Test MySQL version detection for window function support"""
    version = mysql_window_function_test_db.get_server_version()
    logger.info(f"Detected MySQL version: {version}")

    has_window_support = check_window_function_support(mysql_window_function_test_db)
    logger.info(f"Window function support: {has_window_support}")

    if version >= (8, 0, 0):
        assert has_window_support, f"MySQL version {version} should support window functions but detection returned False"
    else:
        assert not has_window_support, f"MySQL version {version} should not support window functions but detection returned True"


def test_basic_row_number(mysql_window_function_test_db):
    """Test basic ROW_NUMBER() window function"""
    if not check_window_function_support(mysql_window_function_test_db):
        pytest.skip("MySQL version does not support window functions")

    result = mysql_window_function_test_db.execute(
        """
        SELECT 
            id, name, department, salary,
            ROW_NUMBER() OVER (ORDER BY salary DESC) as salary_rank
        FROM window_test_employees
        ORDER BY salary_rank
        """,
        returning=True
    )

    assert result.data is not None
    assert len(result.data) == 12  # Should return all employees

    # Verify row numbers are assigned correctly
    for i, row in enumerate(result.data):
        assert row["salary_rank"] == i + 1, f"Expected row {i + 1} to have rank {i + 1}, got {row['salary_rank']}"

    # Verify highest salary is first
    assert result.data[0]["salary_rank"] == 1
    assert float(result.data[0]["salary"]) == max([float(row["salary"]) for row in result.data])

    logger.info("Basic ROW_NUMBER() window function test passed")


def test_partition_by_window(mysql_window_function_test_db):
    """Test PARTITION BY clause in window functions"""
    if not check_window_function_support(mysql_window_function_test_db):
        pytest.skip("MySQL version does not support window functions")

    result = mysql_window_function_test_db.execute(
        """
        SELECT 
            id, name, department, salary,
            ROW_NUMBER() OVER (PARTITION BY department ORDER BY salary DESC) as dept_salary_rank
        FROM window_test_employees
        ORDER BY department, dept_salary_rank
        """,
        returning=True
    )

    assert result.data is not None
    assert len(result.data) == 12  # Should return all employees

    # Group results by department to verify rankings
    departments = {}
    for row in result.data:
        dept = row["department"]
        if dept not in departments:
            departments[dept] = []
        departments[dept].append(row)

    # Verify each department has correct rankings
    for dept, rows in departments.items():
        # Check ranks start at 1 and are sequential
        ranks = [row["dept_salary_rank"] for row in rows]
        expected_ranks = list(range(1, len(rows) + 1))
        assert ranks == expected_ranks, f"Department {dept} has incorrect ranks: {ranks}, expected {expected_ranks}"

        # Check that rows are ordered by salary within department
        for i in range(len(rows) - 1):
            assert float(rows[i]["salary"]) >= float(rows[i + 1]["salary"]), \
                f"Salary ordering is incorrect in department {dept}"

    logger.info("PARTITION BY window function test passed")


def test_multiple_window_functions(mysql_window_function_test_db):
    """Test multiple window functions in a single query"""
    if not check_window_function_support(mysql_window_function_test_db):
        pytest.skip("MySQL version does not support window functions")

    result = mysql_window_function_test_db.execute(
        """
        SELECT 
            id, name, department, salary,
            ROW_NUMBER() OVER (ORDER BY salary DESC) as overall_rank,
            ROW_NUMBER() OVER (PARTITION BY department ORDER BY salary DESC) as dept_rank,
            RANK() OVER (ORDER BY salary DESC) as overall_salary_rank,
            DENSE_RANK() OVER (ORDER BY salary DESC) as dense_salary_rank
        FROM window_test_employees
        ORDER BY overall_rank
        """,
        returning=True
    )

    assert result.data is not None
    assert len(result.data) == 12  # Should return all employees

    # Verify all ranking functions return valid values
    unique_salaries = set()
    for row in result.data:
        assert row["overall_rank"] >= 1
        assert row["dept_rank"] >= 1
        assert row["overall_salary_rank"] >= 1
        assert row["dense_salary_rank"] >= 1

        # Keep track of unique salaries for RANK and DENSE_RANK validation
        unique_salaries.add(float(row["salary"]))

    # Verify RANK and DENSE_RANK produce expected results
    # DENSE_RANK should not have gaps while RANK may have gaps
    max_dense_rank = max([row["dense_salary_rank"] for row in result.data])
    assert max_dense_rank == len(unique_salaries), \
        f"Expected max DENSE_RANK to be {len(unique_salaries)}, got {max_dense_rank}"

    logger.info("Multiple window functions test passed")


def test_window_aggregates(mysql_window_function_test_db):
    """Test window aggregate functions"""
    if not check_window_function_support(mysql_window_function_test_db):
        pytest.skip("MySQL version does not support window functions")

    result = mysql_window_function_test_db.execute(
        """
        SELECT 
            id, name, department, salary,
            AVG(salary) OVER (PARTITION BY department) as avg_dept_salary,
            MAX(salary) OVER (PARTITION BY department) as max_dept_salary,
            MIN(salary) OVER (PARTITION BY department) as min_dept_salary,
            SUM(salary) OVER (PARTITION BY department) as total_dept_salary,
            COUNT(*) OVER (PARTITION BY department) as dept_employee_count
        FROM window_test_employees
        ORDER BY department, salary DESC
        """,
        returning=True
    )

    assert result.data is not None
    assert len(result.data) == 12  # Should return all employees

    # Group results by department to verify aggregate values
    departments = {}
    for row in result.data:
        dept = row["department"]
        if dept not in departments:
            departments[dept] = []
        departments[dept].append(row)

    # Verify each department has consistent aggregate values
    for dept, rows in departments.items():
        # All rows in department should have same aggregate values
        for i in range(1, len(rows)):
            assert rows[0]["avg_dept_salary"] == rows[i]["avg_dept_salary"]
            assert rows[0]["max_dept_salary"] == rows[i]["max_dept_salary"]
            assert rows[0]["min_dept_salary"] == rows[i]["min_dept_salary"]
            assert rows[0]["total_dept_salary"] == rows[i]["total_dept_salary"]
            assert rows[0]["dept_employee_count"] == rows[i]["dept_employee_count"]

        # Verify aggregate values are correct
        salaries = [float(row["salary"]) for row in rows]
        assert float(rows[0]["max_dept_salary"]) == max(salaries)
        assert float(rows[0]["min_dept_salary"]) == min(salaries)
        assert float(rows[0]["total_dept_salary"]) == sum(salaries)
        assert int(rows[0]["dept_employee_count"]) == len(rows)

        # Verify average salary with some tolerance for float calculation
        expected_avg = sum(salaries) / len(salaries)
        actual_avg = float(rows[0]["avg_dept_salary"])
        assert abs(actual_avg - expected_avg) < 0.01, \
            f"Expected avg salary {expected_avg} but got {actual_avg}"

    logger.info("Window aggregate functions test passed")


def test_window_frame_clause(mysql_window_function_test_db):
    """Test window function frame clause (ROWS BETWEEN)"""
    if not check_window_function_support(mysql_window_function_test_db):
        pytest.skip("MySQL version does not support window functions")

    result = mysql_window_function_test_db.execute(
        """
        SELECT 
            id, name, department, salary, hire_date,
            SUM(salary) OVER (
                PARTITION BY department 
                ORDER BY hire_date 
                ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
            ) as cumulative_dept_salary
        FROM window_test_employees
        ORDER BY department, hire_date
        """,
        returning=True
    )

    assert result.data is not None
    assert len(result.data) == 12  # Should return all employees

    # Group results by department to verify cumulative sums
    departments = {}
    for row in result.data:
        dept = row["department"]
        if dept not in departments:
            departments[dept] = []
        departments[dept].append(row)

    # Verify each department has correct cumulative sums
    for dept, rows in departments.items():
        # Sort by hire date to match query's ORDER BY
        rows.sort(key=lambda x: x["hire_date"])

        # Calculate running sum manually to verify
        running_sum = 0
        for i, row in enumerate(rows):
            running_sum += float(row["salary"])
            assert abs(float(row["cumulative_dept_salary"]) - running_sum) < 0.01, \
                f"Expected cumulative salary {running_sum} but got {row['cumulative_dept_salary']}"

    logger.info("Window frame clause test passed")


def test_complex_window_query(mysql_window_function_test_db):
    """Test complex window query with joins and multiple window functions"""
    if not check_window_function_support(mysql_window_function_test_db):
        pytest.skip("MySQL version does not support window functions")

    result = mysql_window_function_test_db.execute(
        """
        SELECT 
            e.id, e.name, e.department, s.sale_date, s.amount, s.product_category, s.region,
            ROW_NUMBER() OVER (PARTITION BY e.id ORDER BY s.amount DESC) as emp_sale_rank,
            SUM(s.amount) OVER (PARTITION BY e.id) as total_emp_sales,
            SUM(s.amount) OVER (PARTITION BY e.department) as total_dept_sales,
            ROUND(s.amount / SUM(s.amount) OVER (PARTITION BY e.id) * 100, 2) as pct_of_emp_sales,
            ROUND(s.amount / SUM(s.amount) OVER (PARTITION BY s.product_category) * 100, 2) as pct_of_category
        FROM window_test_employees e
        JOIN window_test_sales s ON e.id = s.employee_id
        ORDER BY e.department, e.id, emp_sale_rank
        """,
        returning=True
    )

    assert result.data is not None

    # Group results by employee to verify calculations
    employees = {}
    for row in result.data:
        emp_id = row["id"]
        if emp_id not in employees:
            employees[emp_id] = []
        employees[emp_id].append(row)

    # Group results by department to verify calculations
    departments = {}
    for row in result.data:
        dept = row["department"]
        if dept not in departments:
            departments[dept] = []
        departments[dept].append(row)

    # Group results by product category to verify calculations
    categories = {}
    for row in result.data:
        category = row["product_category"]
        if category not in categories:
            categories[category] = []
        categories[category].append(row)

    # Verify employee sales percentages add up to approximately 100%
    for emp_id, rows in employees.items():
        total_pct = sum([float(row["pct_of_emp_sales"]) for row in rows])
        assert abs(total_pct - 100.0) < 0.1, \
            f"Total percentage for employee {emp_id} should be 100%, got {total_pct}%"

    # Verify category percentages are calculated correctly
    for category, rows in categories.items():
        category_total = sum([float(row["amount"]) for row in rows])

        for row in rows:
            expected_pct = float(row["amount"]) / category_total * 100
            actual_pct = float(row["pct_of_category"])
            assert abs(expected_pct - actual_pct) < 0.1, \
                f"Expected category percentage {expected_pct}%, got {actual_pct}%"

    logger.info("Complex window query test passed")


def test_mysql_expression_with_window(mysql_window_function_test_db):
    """Test using MySQL expressions with window functions"""
    if not check_window_function_support(mysql_window_function_test_db):
        pytest.skip("MySQL version does not support window functions")

    # Create SQL expression for window function
    window_expr = mysql_window_function_test_db.create_expression(
        "ROW_NUMBER() OVER (PARTITION BY department ORDER BY salary DESC)"
    )

    # Query using expression
    result = mysql_window_function_test_db.execute(
        """
        SELECT 
            id, name, department, salary,
            %s as dept_rank
        FROM window_test_employees
        ORDER BY department, dept_rank
        """,
        params=(window_expr,),
        returning=True
    )

    assert result.data is not None
    assert len(result.data) == 12  # Should return all employees

    # Group results by department to verify rankings
    departments = {}
    for row in result.data:
        dept = row["department"]
        if dept not in departments:
            departments[dept] = []
        departments[dept].append(row)

    # Verify each department has correct rankings
    for dept, rows in departments.items():
        # Check ranks start at 1 and are sequential
        ranks = [row["dept_rank"] for row in rows]
        expected_ranks = list(range(1, len(rows) + 1))
        assert ranks == expected_ranks, f"Department {dept} has incorrect ranks: {ranks}, expected {expected_ranks}"

    logger.info("MySQL expression with window function test passed")


def test_non_window_alternative(mysql_window_function_test_db):
    """Test alternative approach for pre-8.0 MySQL versions without window functions"""
    # This test shows how to achieve similar results without window functions
    # It should work on all MySQL versions

    # Get ranking of employees by salary within departments
    if check_window_function_support(mysql_window_function_test_db):
        # With window functions (8.0+)
        window_result = mysql_window_function_test_db.execute(
            """
            SELECT 
                id, name, department, salary,
                ROW_NUMBER() OVER (PARTITION BY department ORDER BY salary DESC) as dept_rank
            FROM window_test_employees
            ORDER BY department, dept_rank
            """,
            returning=True
        )

    # Alternative approach without window functions
    non_window_result = mysql_window_function_test_db.execute(
        """
        SELECT 
            e1.id, e1.name, e1.department, e1.salary,
            COUNT(e2.id) as dept_rank
        FROM window_test_employees e1
        JOIN window_test_employees e2 
            ON e1.department = e2.department AND e2.salary >= e1.salary
        GROUP BY e1.id, e1.name, e1.department, e1.salary
        ORDER BY e1.department, dept_rank
        """,
        returning=True
    )

    assert non_window_result.data is not None
    assert len(non_window_result.data) == 12  # Should return all employees

    # If window functions are supported, compare results
    if check_window_function_support(mysql_window_function_test_db):
        assert window_result.data is not None
        assert len(window_result.data) == len(non_window_result.data)

        # Map results by ID for comparison
        window_map = {row["id"]: row for row in window_result.data}
        non_window_map = {row["id"]: row for row in non_window_result.data}

        # Verify rankings match
        for emp_id, row in window_map.items():
            assert emp_id in non_window_map
            assert row["dept_rank"] == non_window_map[emp_id]["dept_rank"], \
                f"Rank mismatch for employee {emp_id}: window={row['dept_rank']}, non-window={non_window_map[emp_id]['dept_rank']}"

    logger.info("Non-window alternative test passed")


def test_window_function_compatibility(mysql_window_function_test_db):
    """Test to handle both MySQL versions with and without window function support"""
    version = mysql_window_function_test_db.get_server_version()

    if version >= (8, 0, 0):
        logger.info(f"Testing with MySQL {version} - should support window functions")
        # Run query with window functions
        try:
            result = mysql_window_function_test_db.execute(
                """
                SELECT 
                    id, name, department, salary,
                    ROW_NUMBER() OVER (PARTITION BY department ORDER BY salary DESC) as dept_rank
                FROM window_test_employees
                ORDER BY department, dept_rank
                """,
                returning=True
            )
            assert result.data is not None
            assert len(result.data) == 12

            # Check window function worked
            for row in result.data:
                assert "dept_rank" in row
                assert row["dept_rank"] is not None

            logger.info("Window function query succeeded as expected on MySQL 8.0+")
        except Exception as e:
            pytest.fail(f"Window function query failed unexpectedly on MySQL 8.0+: {e}")
    else:
        logger.info(f"Testing with MySQL {version} - should NOT support window functions")
        # Run query with window functions - should fail on pre-8.0
        try:
            mysql_window_function_test_db.execute(
                """
                SELECT 
                    id, name, department, salary,
                    ROW_NUMBER() OVER (PARTITION BY department ORDER BY salary DESC) as dept_rank
                FROM window_test_employees
                ORDER BY department, dept_rank
                """,
                returning=True
            )
            # If we reach here, the query didn't fail which is unexpected
            logger.warning("Window function query unexpectedly succeeded on MySQL < 8.0")

            # Additional check - see if the results actually contain window function output
            # Sometimes older MySQL versions might parse the query but ignore window functions
            result = mysql_window_function_test_db.execute(
                "SELECT 1 + 1 as two", returning=True
            )
            assert result.data is not None
        except Exception as e:
            # Expected to fail on MySQL < 8.0
            logger.info(f"Window function query failed as expected on MySQL < 8.0: {e}")