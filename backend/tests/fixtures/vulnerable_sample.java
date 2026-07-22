// Deliberately vulnerable/smelly sample code — used ONLY to validate that the Code Analysis and
// Security Vulnerability agents actually detect known issues (Milestone 2, Task 4). Never
// compile or execute this file; it exists purely as static text for the agents to analyze.
import java.sql.*;
import java.security.MessageDigest;

public class VulnerableSample {
    private String apiKey = "AKIAFAKETESTKEY0";
    private String dbPassword = "SuperSecret123!";

    public User getUserById(String userId) throws Exception {
        Connection conn = DriverManager.getConnection("jdbc:sqlite:app.db");
        Statement stmt = conn.createStatement();
        String query = "SELECT * FROM users WHERE id = " + userId;
        ResultSet rs = stmt.executeQuery(query);
        return null;
    }

    public String hashPassword(String password) throws Exception {
        MessageDigest md = MessageDigest.getInstance("MD5");
        return null;
    }

    public void reflectInput(HttpServletRequest request, HttpServletResponse response) throws Exception {
        response.getWriter().println(request.getParameter("name"));
    }

    protected void configure(HttpSecurity http) throws Exception {
        http.csrf().disable();
    }

    public void deeplyNestedAndOverParameterized(int a, int b, int c, int d, int e, int f) {
        if (a > 0) {
            if (b > 0) {
                if (c > 0) {
                    if (d > 0) {
                        if (e > 0) {
                            System.out.println("deep");
                        }
                    }
                }
            }
        }
        try {
            riskyOperation();
        } catch (Exception ex) {
        }
    }

    public void methodOne() {}
    public void methodTwo() {}
    public void methodThree() {}
    public void methodFour() {}
    public void methodFive() {}
    public void methodSix() {}
    public void methodSeven() {}
    public void methodEight() {}
    public void methodNine() {}
    public void methodTen() {}
    public void methodEleven() {}
    public void methodTwelve() {}
    public void methodThirteen() {}
    public void methodFourteen() {}
    public void methodFifteen() {}
    public void methodSixteen() {}
}
