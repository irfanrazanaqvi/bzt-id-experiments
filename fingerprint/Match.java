import com.machinezoo.sourceafis.*;
import java.io.PrintWriter;
import java.nio.file.*;
import java.util.*;
public class Match {
    static FingerprintTemplate load(String p) {
        try { return new FingerprintTemplate(new FingerprintImage(Files.readAllBytes(Path.of(p)), new FingerprintImageOptions().dpi(500))); }
        catch (Exception e) { throw new RuntimeException(p, e); }
    }
    public static void main(String[] a) throws Exception {
        List<String> lines = Files.readAllLines(Path.of(a[0]));
        Map<String, FingerprintTemplate> cache = new HashMap<>();
        try (PrintWriter out = new PrintWriter(a[1])) {
            out.println("split,genuine,cosine,kind");
            for (String l : lines.subList(1, lines.size())) {
                String[] p = l.split(",");
                FingerprintTemplate ta = cache.computeIfAbsent(p[3], Match::load), tb = cache.computeIfAbsent(p[4], Match::load);
                double s = new FingerprintMatcher(ta).match(tb);
                out.println(p[0] + "," + p[1] + "," + s + "," + p[2]);
            }
        }
    }
}
