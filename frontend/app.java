import java.io.*;
import java.util.*;

class SolutionClass {
    public static void main(String[] args) throws java.lang.Exception {
        Scanner sc = new Scanner(System.in);
        
        char c = sc.nextLine().charAt(0);
        
        char result = (char)(c ^ 32);
        
        System.out.println(result);
        
        sc.close();
    }
}