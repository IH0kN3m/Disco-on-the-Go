// Original static-analysis automation. Decompiled game material stays in artifacts.
//@category Disco.Analysis
import ghidra.app.script.GhidraScript;
import ghidra.app.cmd.disassemble.DisassembleCommand;
import ghidra.app.decompiler.DecompInterface;
import ghidra.app.decompiler.DecompileResults;
import ghidra.program.model.address.*;
import ghidra.program.model.listing.*;
import ghidra.program.model.symbol.SourceType;
import java.nio.file.*;
import java.util.*;

public class ExportNativeMemory extends GhidraScript {
    public void run() throws Exception {
        String[] args = getScriptArgs();
        if (args.length != 2 || !(args[1].equals("gameassembly") || args[1].equals("amplify")))
            throw new IllegalArgumentException("Expected private output directory and inspected binary kind");
        Path root = Paths.get(args[0]).toRealPath();
        Path code = root.resolve("decompiled");
        Files.createDirectories(code);
        List<String> labels = Files.readAllLines(root.resolve("labels.tsv"));
        List<String> targets = Files.readAllLines(root.resolve("targets.tsv"));
        List<String> boundaries = Files.readAllLines(root.resolve("functions.tsv"));
        if (labels.size() > 150000 || targets.isEmpty() || targets.size() > 1000)
            throw new IllegalArgumentException("Unsupported analysis manifest size");
        for (String line : labels) {
            String[] row = line.split("\t", -1);
            if (row.length != 2 || !row[1].matches("[a-zA-Z0-9_]{1,160}"))
                throw new IllegalArgumentException("Invalid method label");
            Address address = toAddr(Long.parseUnsignedLong(row[0], 16));
            if (!currentProgram.getMemory().contains(address)) throw new IllegalArgumentException("Unowned label");
            createLabel(address, row[1], true, SourceType.USER_DEFINED);
        }
        println("Native method labels imported: " + labels.size());
        if (boundaries.isEmpty() || boundaries.size() > 250000)
            throw new IllegalArgumentException("Unsupported native boundary count");
        // Mach-O LC_FUNCTION_STARTS supplies actual boundaries, including generic
        // instantiations without managed method pointers. Defining callees keeps
        // the decompiler from treating their tails as local control flow.
        for (String line : boundaries) {
            String[] row = line.split("\t", -1);
            if (row.length != 3 || !row[2].matches("[a-zA-Z0-9_]{1,160}"))
                throw new IllegalArgumentException("Invalid native target");
            Address begin = toAddr(Long.parseUnsignedLong(row[0], 16));
            Address end = toAddr(Long.parseUnsignedLong(row[1], 16));
            long length = end.subtract(begin);
            if (length <= 0 || length > 1048576 || !currentProgram.getMemory().contains(end.subtract(1)))
                throw new IllegalArgumentException("Unowned native function span");
            AddressSet body = new AddressSet(begin, end.subtract(1));
            Function function = getFunctionAt(begin);
            if (function == null) function = currentProgram.getFunctionManager().createFunction(row[2], begin, body, SourceType.USER_DEFINED);
            else { function.setBody(body); function.setName(row[2], SourceType.USER_DEFINED); }
        }
        // Verified on this reference: null-reference throw and exception raise
        // wrappers reach __cxa_throw. Bounds-exception construction RETURNS and
        // must not be marked this way.
        for (long address : args[1].equals("gameassembly") ? new long[]{0x3cde24, 0x3cddf0, 0x3644f0, 0x36639c, 0x3663b4} : new long[]{}) {
            Function function = getFunctionAt(toAddr(address));
            if (function == null) throw new IllegalStateException("Missing exception boundary");
            function.setNoReturn(true);
        }
        println("Native function boundaries imported: " + boundaries.size());
        List<Function> functions = new ArrayList<>();
        for (String line : targets) {
            String[] row = line.split("\t", -1);
            Function function = getFunctionAt(toAddr(Long.parseUnsignedLong(row[0], 16)));
            AddressSet seeds = new AddressSet();
            // Decode every aligned instruction in the selected span, including
            // switch cases not reachable until jump tables are reconstructed.
            // Exported listing provides an independent check against pseudocode.
            for (Address address = function.getEntryPoint(); address.compareTo(function.getBody().getMaxAddress()) <= 0; address = address.add(4))
                seeds.add(address);
            DisassembleCommand command = new DisassembleCommand(seeds, function.getBody(), false);
            command.enableCodeAnalysis(false);
            if (!command.applyTo(currentProgram, monitor)) throw new IllegalStateException("Disassembly failed: " + function.getEntryPoint());
            functions.add(function);
        }
        DecompInterface decompiler = new DecompInterface();
        if (!decompiler.openProgram(currentProgram)) throw new IllegalStateException("Decompiler rejected program");
        int completed = 0, failed = 0;
        try {
            for (Function function : functions) {
                monitor.checkCancelled();
                DecompileResults result = decompiler.decompileFunction(function, 90, monitor);
                String stem = function.getEntryPoint().toString();
                if (!result.decompileCompleted() || result.getDecompiledFunction() == null) {
                    Files.writeString(code.resolve(stem + ".error.txt"), result.getErrorMessage());
                    failed++; println("FAILED " + function.getName()); continue;
                }
                Files.writeString(code.resolve(stem + ".c"), "/* Static pseudocode; unresolved types/calls are not recovered source. */\n" + result.getDecompiledFunction().getC());
                StringBuilder calls = new StringBuilder();
                StringBuilder listing = new StringBuilder();
                InstructionIterator instructions = currentProgram.getListing().getInstructions(function.getBody(), true);
                while (instructions.hasNext()) {
                    Instruction instruction = instructions.next();
                    listing.append(instruction.getAddress()).append("\t").append(instruction).append("\n");
                    if (!instruction.getFlowType().isCall()) continue;
                    Address[] flows = instruction.getFlows();
                    if (flows.length == 0) calls.append(instruction.getAddress()).append("\tindirect\n");
                    for (Address flow : flows) calls.append(instruction.getAddress()).append("\t").append(flow).append("\t").append(getSymbolAt(flow)).append("\n");
                }
                Files.writeString(code.resolve(stem + ".calls.tsv"), calls.toString());
                Files.writeString(code.resolve(stem + ".asm.tsv"), listing.toString());
                completed++; println("DECOMPILED " + function.getName());
            }
        } finally { decompiler.dispose(); }
        Files.writeString(root.resolve("decompilation.json"), "{\"completed\":" + completed + ",\"failed\":" + failed + "}\n");
    }
}
